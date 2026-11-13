from datetime import timedelta

import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.admin_panel.models import BreakGlassRequest
from apps.admin_panel.services import (
    approve_break_glass,
    request_break_glass,
    use_break_glass,
)
from apps.clubroom.models import Clubroom, Membership
from apps.clubroom.permissions import OWNER
from apps.clubroom.services import create_clubroom
from apps.core.audit import AuditEntry
from apps.feed.models import EVENT_BREAK_GLASS_ACCESS, FeedEvent, Notification
from apps.playbook.models import Challenge
from apps.points.models import Reward
from apps.roulette.models import Deck, Match, Question, SecretAnswer
from apps.wishes.models import Wish
from apps.wishes.services import create_wish

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


def make_superuser(username, email):
    return User.objects.create_superuser(
        username=username, email=email, password="sehr-geheim-1234"
    )


def test_secret_models_are_not_registered():
    registry = admin.site._registry
    assert SecretAnswer not in registry
    assert Match not in registry
    assert Wish not in registry
    assert FeedEvent not in registry
    with pytest.raises(NoReverseMatch):
        reverse("admin:roulette_secretanswer_changelist")
    with pytest.raises(NoReverseMatch):
        reverse("admin:wishes_wish_changelist")


def test_content_models_are_registered():
    registry = admin.site._registry
    for model in (Deck, Question, Reward, Challenge, Clubroom):
        assert model in registry


def test_admin_banner_and_missing_safe_word(client):
    clubroom, anna, _ = make_room()
    superuser = make_superuser("root", "root@example.com")
    client.force_login(superuser)
    index = client.get(reverse("admin:index"))
    assert index.status_code == 200
    assert "Zugriff protokolliert" in index.content.decode()

    change = client.get(reverse("admin:clubroom_clubroom_change", args=[clubroom.pk]))
    assert change.status_code == 200
    content = change.content.decode()
    assert "safe_word" not in content
    assert "Anker" not in content


def test_secret_models_have_no_admin_route(client):
    superuser = make_superuser("root", "root@example.com")
    client.force_login(superuser)
    assert client.get("/admin/roulette/secretanswer/").status_code == 404
    assert client.get("/admin/wishes/wish/").status_code == 404


def test_dashboard_is_staff_only_and_shows_no_content(client):
    clubroom, anna, _ = make_room()
    create_wish(
        clubroom=clubroom,
        user=anna,
        wish_type="fantasie",
        title="GEHEIMER TITEL",
        body="GEHEIMER INHALT",
    )
    superuser = make_superuser("root", "root@example.com")
    client.force_login(superuser)
    response = client.get(reverse("admin_panel:dashboard"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Zugriff protokolliert" in content
    assert "GEHEIMER TITEL" not in content
    assert "GEHEIMER INHALT" not in content

    outsider = User.objects.create_user(
        username="out", email="out@example.com", password="sehr-geheim-1234"
    )
    client.force_login(outsider)
    assert client.get(reverse("admin_panel:dashboard")).status_code == 302


def test_audit_admin_is_read_only(client):
    superuser = make_superuser("root", "root@example.com")
    client.force_login(superuser)
    assert client.get(reverse("admin:core_auditentry_changelist")).status_code == 200
    assert client.get(reverse("admin:core_auditentry_add")).status_code == 403


def test_sensitive_targets_are_blocked():
    clubroom, anna, _ = make_room()
    root = make_superuser("root", "root@example.com")
    for target_type in (
        "roulette.secretanswer",
        "roulette.boundary",
        "wishes.wish",
        "wishes.fantasywish",
    ):
        with pytest.raises(ValidationError):
            request_break_glass(
                user=root,
                target_type=target_type,
                target_id="1",
                reason="Test",
            )
    with pytest.raises(ValidationError):
        request_break_glass(
            user=root,
            target_type="accounts.user",
            target_id=str(anna.pk),
            reason="Test",
        )


def test_four_eyes_and_24h_window():
    clubroom, anna, bea = make_room()
    root = make_superuser("root", "root@example.com")
    second = make_superuser("second", "second@example.com")
    membership = Membership.objects.filter(clubroom=clubroom, user=anna).get()

    request_obj = request_break_glass(
        user=root,
        target_type="clubroom.membership",
        target_id=str(membership.pk),
        reason="Missbrauchsverdacht",
    )
    assert request_obj.status == "pending"
    with pytest.raises(ValidationError):
        approve_break_glass(request_obj=request_obj, user=root)
    request_obj.refresh_from_db()
    assert request_obj.status == "pending"

    approve_break_glass(request_obj=request_obj, user=second)
    request_obj.refresh_from_db()
    assert request_obj.status == "approved"
    assert request_obj.expires_at - request_obj.approved_at == timedelta(hours=24)

    before = Notification.objects.count()
    use_break_glass(request_obj=request_obj, user=root)
    request_obj.refresh_from_db()
    assert request_obj.status == "used"
    assert request_obj.users_notified is True
    assert Notification.objects.count() == before + 2
    for notification in Notification.objects.filter(event_type=EVENT_BREAK_GLASS_ACCESS):
        assert notification.delivered_at is not None
    assert not hasattr(Notification, "body")
    with pytest.raises(ValidationError):
        use_break_glass(request_obj=request_obj, user=root)


def test_expired_request_cannot_be_used():
    clubroom, anna, _ = make_room()
    root = make_superuser("root", "root@example.com")
    second = make_superuser("second", "second@example.com")
    membership = Membership.objects.filter(clubroom=clubroom, user=anna).get()
    request_obj = request_break_glass(
        user=root,
        target_type="clubroom.membership",
        target_id=str(membership.pk),
        reason="Test",
    )
    approve_break_glass(request_obj=request_obj, user=second)
    BreakGlassRequest.objects.filter(pk=request_obj.pk).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )
    request_obj.refresh_from_db()
    assert request_obj.status == "expired"
    with pytest.raises(ValidationError):
        use_break_glass(request_obj=request_obj, user=root)


def test_third_superuser_cannot_use_request():
    clubroom, anna, _ = make_room()
    root = make_superuser("root", "root@example.com")
    second = make_superuser("second", "second@example.com")
    third = make_superuser("third", "third@example.com")
    membership = Membership.objects.filter(clubroom=clubroom, user=anna).get()
    request_obj = request_break_glass(
        user=root,
        target_type="clubroom.membership",
        target_id=str(membership.pk),
        reason="Test",
    )
    approve_break_glass(request_obj=request_obj, user=second)
    with pytest.raises(ValidationError):
        use_break_glass(request_obj=request_obj, user=third)


def test_non_superuser_cannot_request_or_approve():
    clubroom, anna, bea = make_room()
    staff = User.objects.create_user(
        username="staff",
        email="staff@example.com",
        password="sehr-geheim-1234",
        is_staff=True,
    )
    membership = Membership.objects.filter(clubroom=clubroom, user=anna).get()
    with pytest.raises(ValidationError):
        request_break_glass(
            user=staff,
            target_type="clubroom.membership",
            target_id=str(membership.pk),
            reason="Test",
        )


def test_released_match_can_be_targeted_but_unreleased_not():
    from apps.roulette.models import Deck
    from apps.roulette.services import release_match, start_round, submit_answer

    clubroom, anna, bea = make_room()
    root = make_superuser("root", "root@example.com")
    deck = Deck.objects.get(code="A")
    round_obj = start_round(clubroom=clubroom, deck=deck, user=anna)
    question = round_obj.deck.questions.first()
    submit_answer(
        round_obj=round_obj,
        question=question,
        user=anna,
        answer="ja",
        is_boundary=False,
    )
    submit_answer(
        round_obj=round_obj,
        question=question,
        user=bea,
        answer="ja",
        is_boundary=False,
    )
    match = Match.objects.get(round=round_obj)
    with pytest.raises(ValidationError):
        request_break_glass(
            user=root,
            target_type="roulette.match",
            target_id=str(match.pk),
            reason="Test",
        )
    release_match(match=match, user=anna)
    release_match(match=match, user=bea)
    request_obj = request_break_glass(
        user=root,
        target_type="roulette.match",
        target_id=str(match.pk),
        reason="Freigegebener Match",
    )
    assert request_obj.target_type == "roulette.match"


def test_break_glass_audit_chain_and_banner(client):
    clubroom, anna, _ = make_room()
    root = make_superuser("root", "root@example.com")
    second = make_superuser("second", "second@example.com")
    membership = Membership.objects.filter(clubroom=clubroom, user=anna).get()
    request_obj = request_break_glass(
        user=root,
        target_type="clubroom.membership",
        target_id=str(membership.pk),
        reason="Test",
    )
    approve_break_glass(request_obj=request_obj, user=second)
    use_break_glass(request_obj=request_obj, user=root)

    actions = list(AuditEntry.objects.order_by("id").values_list("action", flat=True))
    assert actions[-3:] == [
        "break_glass.request",
        "break_glass.approve",
        "break_glass.use",
    ]
    ok, broken_pk, reason = AuditEntry.verify_chain()
    assert ok is True and broken_pk is None

    client.force_login(root)
    response = client.get(reverse("admin_panel:break_glass"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Zugriff protokolliert" in content
    assert "Geheimantworten" in content
