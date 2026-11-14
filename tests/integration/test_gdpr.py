import json
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.gdpr import export_user_data
from apps.accounts.models import User
from apps.clubroom.models import Clubroom, Membership
from apps.clubroom.permissions import OWNER
from apps.clubroom.services import create_clubroom
from apps.core.crypto import decrypt_text, encrypt_text
from apps.feed.models import NotificationChannel, NotificationSubscription
from apps.lounge.models import CheckIn
from apps.points.models import Ledger
from apps.points.services import award_points, get_or_create_ledger
from apps.roulette.models import Deck, SecretAnswer
from apps.roulette.services import start_round, submit_answer
from apps.wishes.models import ACTION_ALTERNATIVE, STATUS_REJECTED, Wish, WishResponse
from apps.wishes.services import (
    create_wish,
    purge_rejected_wishes,
    respond_to_wish,
)

pytestmark = pytest.mark.django_db


def make_room():
    anna = User.objects.create_user(
        username="anna", email="anna@example.com", password="sehr-geheim-1234"
    )
    bea = User.objects.create_user(
        username="bea", email="bea@example.com", password="sehr-geheim-1234"
    )
    clubroom = create_clubroom(user=anna, name="Unser Raum", safe_word="Anker")
    Membership.objects.create(clubroom=clubroom, user=bea, role=OWNER)
    return clubroom, anna, bea


def test_export_contains_own_data_but_no_partner_secrets(client):
    clubroom, anna, bea = make_room()
    own_wish = create_wish(
        clubroom=clubroom,
        user=anna,
        wish_type="fantasie",
        title="Mein Titel",
        body="Mein GEHEIMER Inhalt",
    )
    partner_wish = create_wish(
        clubroom=clubroom,
        user=bea,
        wish_type="fantasie",
        title="Partner Titel",
        body="Partner GEHEIMER Inhalt",
    )
    respond_to_wish(
        wish=partner_wish,
        user=anna,
        action=ACTION_ALTERNATIVE,
        note="Meine Alternative",
    )
    CheckIn.objects.create(clubroom=clubroom, user=anna, mood=4, energy=3, closeness=5)
    channel = NotificationChannel.objects.create(
        clubroom=clubroom, provider="telegram", label="Testkanal", is_enabled=True
    )
    channel.set_config({"bot_token": "secret", "default_target": "42"})
    channel.save()
    NotificationSubscription.objects.create(channel=channel, user=anna, destination="MEIN-ZIEL")

    client.force_login(anna)
    response = client.get(reverse("accounts:export"))
    assert response.status_code == 200
    assert "attachment" in response["Content-Disposition"]
    payload = json.loads(response.content)
    serialized = json.dumps(payload, ensure_ascii=False)
    assert payload["account"]["email"] == "anna@example.com"
    assert "Mein GEHEIMER Inhalt" in serialized
    assert "Meine Alternative" in serialized
    assert "MEIN-ZIEL" in serialized
    assert "Testkanal" in serialized
    assert "Partner GEHEIMER Inhalt" not in serialized
    assert "Anker" not in serialized
    assert str(own_wish.pk) in serialized or own_wish.title in serialized

    export_user_data(anna)


def test_delete_requires_password_and_anonymizes(client):
    clubroom, anna, bea = make_room()
    own_wish = create_wish(
        clubroom=clubroom,
        user=anna,
        wish_type="konkret",
        title="Eigener Titel",
        body="Eigener Inhalt",
    )
    partner_wish = create_wish(
        clubroom=clubroom,
        user=bea,
        wish_type="konkret",
        title="Partner Titel",
        body="Partner Inhalt",
    )
    respond_to_wish(
        wish=partner_wish,
        user=anna,
        action=ACTION_ALTERNATIVE,
        note="Annas Notiz",
    )
    CheckIn.objects.create(clubroom=clubroom, user=anna, mood=3, energy=3, closeness=3)
    get_or_create_ledger(clubroom, anna)
    award_points(clubroom=clubroom, user=anna, amount=2, reason="wish.confirmed", actor=bea)

    client.force_login(anna)
    response = client.post(
        reverse("accounts:delete"),
        {"password": "falsch", "confirm": "1"},
        follow=True,
    )
    assert response.status_code == 200
    anna.refresh_from_db()
    assert anna.is_active is True

    response = client.post(
        reverse("accounts:delete"),
        {"password": "sehr-geheim-1234", "confirm": "1"},
        follow=True,
    )
    assert response.status_code == 200
    anna.refresh_from_db()
    assert anna.is_active is False
    assert anna.username.startswith("deleted-")
    assert anna.email.endswith("@invalid")
    assert anna.check_password("sehr-geheim-1234") is False
    assert not Membership.objects.filter(user=anna, revoked_at__isnull=True).exists()
    assert CheckIn.objects.filter(user=anna).count() == 0
    assert Ledger.objects.filter(owner=anna).count() == 0
    assert NotificationSubscription.objects.filter(user=anna).count() == 0

    own_wish.refresh_from_db()
    assert own_wish.body == ""
    assert own_wish.title == "Gelöschter Wunsch"
    partner_wish.refresh_from_db()
    assert partner_wish.body == "Partner Inhalt"
    assert WishResponse.objects.get(responded_by=anna).note == ""
    assert User.objects.filter(pk=anna.pk, is_active=False).exists()
    assert anna.memberships.filter(revoked_at__isnull=True).count() == 0


def test_delete_command_requires_confirm_and_works():
    _, anna, _ = make_room()
    with pytest.raises(CommandError):
        call_command("gdpr_delete", user="anna")
    call_command("gdpr_delete", user="anna", confirm=True)
    anna.refresh_from_db()
    assert anna.is_active is False


def test_export_command_writes_json(tmp_path):
    clubroom, anna, _ = make_room()
    output = tmp_path / "export.json"
    call_command("gdpr_export", user="anna", output=str(output))
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["account"]["username"] == "anna"


def test_rejected_wishes_are_purged_after_retention():
    clubroom, anna, bea = make_room()
    wish = create_wish(
        clubroom=clubroom,
        user=anna,
        wish_type="offen",
        title="Alter Wunsch",
        body="Alter Inhalt",
    )
    respond_to_wish(
        wish=wish,
        user=bea,
        action=ACTION_ALTERNATIVE,
        note="Alte Notiz",
    )
    Wish.objects.filter(pk=wish.pk).update(
        status=STATUS_REJECTED, updated_at=timezone.now() - timedelta(days=100)
    )
    assert purge_rejected_wishes(days=90) == 1
    wish.refresh_from_db()
    assert wish.title == "Gelöschter Wunsch"
    assert wish.body == ""
    assert WishResponse.objects.get(wish=wish).note == ""


def test_key_rotation_reencrypts_all_sensitive_fields():
    old_key = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    new_key = "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE="
    with override_settings(FIELD_ENCRYPTION_KEY=old_key, FIELD_ENCRYPTION_KEY_OLD=""):
        clubroom, anna, bea = make_room()
        wish = create_wish(
            clubroom=clubroom,
            user=anna,
            wish_type="fantasie",
            title="Rotation",
            body="Geheimer Rotationsinhalt",
        )
        respond_to_wish(
            wish=wish,
            user=bea,
            action=ACTION_ALTERNATIVE,
            note="Rotationsnotiz",
        )
        channel = NotificationChannel.objects.create(
            clubroom=clubroom, provider="gotify", label="Rotation", is_enabled=True
        )
        channel.set_config({"server_url": "https://gotify.example", "app_token": "GEHEIM"})
        channel.save()
        subscription = NotificationSubscription.objects.create(
            channel=channel, user=anna, destination="GEHEIM-ZIEL"
        )
        round_obj = start_round(clubroom=clubroom, deck=Deck.objects.get(code="A"), user=anna)
        secret = submit_answer(
            round_obj=round_obj,
            question=round_obj.deck.questions.first(),
            user=anna,
            answer="ja",
            is_boundary=False,
        )
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT safe_word FROM clubroom_clubroom WHERE id = %s", [clubroom.pk])
            old_ciphertext = cursor.fetchone()[0]

    with override_settings(FIELD_ENCRYPTION_KEY=new_key, FIELD_ENCRYPTION_KEY_OLD=old_key):
        assert decrypt_text(old_ciphertext) == "Anker"
        call_command("encrypt_rotate")
        with connection.cursor() as cursor:
            cursor.execute("SELECT safe_word FROM clubroom_clubroom WHERE id = %s", [clubroom.pk])
            new_ciphertext = cursor.fetchone()[0]
        assert new_ciphertext != old_ciphertext
        assert decrypt_text(new_ciphertext) == "Anker"

    with override_settings(FIELD_ENCRYPTION_KEY=new_key, FIELD_ENCRYPTION_KEY_OLD=""):
        assert Clubroom.objects.get(pk=clubroom.pk).safe_word == "Anker"
        assert Wish.objects.get(pk=wish.pk).body == "Geheimer Rotationsinhalt"
        assert WishResponse.objects.get(wish=wish).note == "Rotationsnotiz"
        assert SecretAnswer.objects.get(pk=secret.pk).answer == "ja"
        channel.refresh_from_db()
        subscription.refresh_from_db()
        assert channel.get_config()["app_token"] == "GEHEIM"
        assert subscription.destination == "GEHEIM-ZIEL"
        assert encrypt_text("Test").startswith("enc:v1:")
