import pytest
from django.db import connection
from django.urls import reverse

from apps.accounts.models import User
from apps.clubroom.models import Membership
from apps.clubroom.permissions import GUEST, OWNER
from apps.clubroom.services import create_clubroom
from apps.lounge.models import CheckIn
from apps.messaging.models import Message

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


def test_mood_dashboard_accepts_time_filters(client):
    clubroom, anna, _ = make_room()
    CheckIn.objects.create(clubroom=clubroom, user=anna, mood=4, energy=3, closeness=5)
    client.force_login(anna)
    response = client.get(reverse("mood"), {"tage": 7})
    assert response.status_code == 200
    assert "Stimmungsverlauf" in response.content.decode()
    assert response.context["days"] == 7


def test_messages_are_encrypted_and_only_for_owners(client):
    clubroom, anna, bea = make_room()
    client.force_login(anna)
    response = client.post(reverse("messaging:index"), {"body": "Nur für uns"})
    assert response.status_code == 302
    message = Message.objects.get()
    with connection.cursor() as cursor:
        cursor.execute("SELECT body FROM messaging_message WHERE id = %s", [message.pk])
        stored = cursor.fetchone()[0]
    assert stored.startswith("enc:v1:")
    assert "Nur für uns" not in stored

    client.force_login(bea)
    assert "Nur für uns" in client.get(reverse("messaging:index")).content.decode()
    guest = User.objects.create_user(
        username="gast", email="gast@example.com", password="sehr-geheim-1234"
    )
    Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    client.force_login(guest)
    assert client.get(reverse("messaging:index")).status_code == 403


def test_existing_owner_gets_new_modules_from_role_defaults(client):
    clubroom, anna, _ = make_room()
    membership = Membership.objects.get(clubroom=clubroom, user=anna)
    membership.module_permissions = {}
    membership.save(update_fields=["module_permissions"])
    assert membership.has_module_access("messages")
    client.force_login(anna)
    response = client.get(reverse("clubroom:home"))
    assert response.context["nav_modules"]["messages"] is True
    assert "Chat" in response.content.decode()


def test_unread_message_badge_context(client):
    clubroom, anna, bea = make_room()
    Message.objects.create(clubroom=clubroom, sender=bea, body="Hallo")
    client.force_login(anna)
    response = client.get(reverse("clubroom:home"))
    assert response.context["nav_unread_messages"] == 1
    assert "Chat" in response.content.decode()
    client.get(reverse("messaging:index"))
    response = client.get(reverse("clubroom:home"))
    assert response.context["nav_unread_messages"] == 0


def test_quick_message(client):
    clubroom, anna, bea = make_room()
    client.force_login(anna)
    response = client.post(reverse("messaging:quick"), {"quick_key": "herz"})
    assert response.status_code == 302
    message = Message.objects.get()
    assert message.kind == "quick"
    assert message.quick_key == "herz"
    client.force_login(bea)
    assert "Herz" in client.get(reverse("messaging:index")).content.decode()
