from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.clubroom.models import Membership
from apps.clubroom.permissions import GUEST, MODERATOR, OWNER
from apps.clubroom.services import create_clubroom
from apps.feed.models import (
    EVENT_CHECKIN_CREATED,
    EVENT_WISH_CREATED,
    FeedEvent,
    Notification,
    sanitize_metadata,
)
from apps.feed.services import record_event
from apps.lounge.models import CheckIn, WeeklyReviewOptIn
from apps.lounge.services import (
    barometer,
    create_check_in,
    set_safe_mode,
    toggle_weekly_review,
    weekly_review,
)
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


def test_check_in_is_unique_per_day_and_creates_event():
    clubroom, anna, bea = make_room()
    check_in = create_check_in(clubroom=clubroom, user=anna, mood=4, energy=3, closeness=5)
    assert check_in.date == timezone.localdate()
    assert FeedEvent.objects.filter(event_type=EVENT_CHECKIN_CREATED).exists()
    assert Notification.objects.filter(user=bea).count() == 1

    with pytest.raises(ValidationError):
        create_check_in(clubroom=clubroom, user=anna, mood=2, energy=2, closeness=2)


def test_barometer_only_uses_last_three_days():
    clubroom, anna, bea = make_room()
    today = timezone.localdate()
    CheckIn.objects.create(clubroom=clubroom, user=anna, date=today, mood=5, energy=4, closeness=5)
    CheckIn.objects.create(
        clubroom=clubroom,
        user=bea,
        date=today - timedelta(days=2),
        mood=1,
        energy=2,
        closeness=1,
    )
    CheckIn.objects.create(
        clubroom=clubroom,
        user=anna,
        date=today - timedelta(days=4),
        mood=5,
        energy=5,
        closeness=5,
    )
    result = barometer(clubroom)
    assert result["overall"]["mood"] == 3.0
    assert sum(row["count"] for row in result["per_user"]) == 2


def test_weekly_review_is_opt_in_and_personal():
    clubroom, anna, bea = make_room()
    assert toggle_weekly_review(clubroom=clubroom, user=anna) is True
    assert WeeklyReviewOptIn.objects.filter(clubroom=clubroom, user=anna).exists()
    CheckIn.objects.create(clubroom=clubroom, user=anna, mood=5, energy=4, closeness=5)
    CheckIn.objects.create(clubroom=clubroom, user=bea, mood=1, energy=1, closeness=1)
    review = weekly_review(clubroom, anna)
    assert review["count"] == 1
    assert review["averages"]["mood"] == 5.0


def test_guest_can_view_lounge_but_not_check_in(client):
    clubroom, anna, _ = make_room()
    guest = User.objects.create_user(
        username="gast", email="gast@example.com", password="sehr-geheim-1234"
    )
    Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    client.force_login(guest)
    assert client.get(reverse("lounge:index")).status_code == 200
    client.post(
        reverse("lounge:check_in"),
        {"mood": 3, "energy": 3, "closeness": 3},
    )
    assert CheckIn.objects.filter(user=guest).count() == 0


def test_safe_mode_queues_and_flushes_without_content(client):
    clubroom, anna, bea = make_room()
    bea.is_safe_mode_active = True
    bea.save(update_fields=["is_safe_mode_active"])

    create_wish(
        clubroom=clubroom,
        user=anna,
        wish_type="konkret",
        title="Sicherer Wunsch",
        body="Sicherer Inhalt",
    )
    queued = Notification.objects.get(user=bea)
    assert queued.delivered_at is None
    assert queued.queued_during_safe_mode is True

    client.force_login(bea)
    response = client.post(reverse("lounge:safe_mode"), {"active": "0"}, follow=True)
    assert response.status_code == 200
    queued.refresh_from_db()
    assert queued.delivered_at is not None
    assert "ohne Inhalt" in response.content.decode()
    bea.refresh_from_db()
    assert bea.is_safe_mode_active is False


def test_safe_mode_toggle_creates_no_event_or_notification(client):
    clubroom, anna, bea = make_room()
    before_events = FeedEvent.objects.count()
    before_notifications = Notification.objects.count()
    client.force_login(bea)
    client.post(reverse("lounge:safe_mode"), {"active": "1"})
    assert FeedEvent.objects.count() == before_events
    assert Notification.objects.count() == before_notifications


def test_feed_contains_no_secret_content(client):
    clubroom, anna, bea = make_room()
    create_wish(
        clubroom=clubroom,
        user=anna,
        wish_type="fantasie",
        title="Titel GEHEIM",
        body="Inhalt GEHEIM",
    )
    client.force_login(bea)
    content = client.get(reverse("feed:index")).content.decode()
    assert "Titel GEHEIM" not in content
    assert "Inhalt GEHEIM" not in content
    assert "Wunsch gestellt" in content

    event = FeedEvent.objects.filter(event_type=EVENT_WISH_CREATED).first()
    assert "Titel GEHEIM" not in str(event.metadata)
    assert "Inhalt GEHEIM" not in str(event.metadata)


def test_sanitize_metadata_drops_sensitive_keys():
    cleaned = sanitize_metadata(
        {
            "type": "konkret",
            "title": "GEHEIM",
            "body": "GEHEIM",
            "note": "GEHEIM",
            "answer": "GEHEIM",
            "safe_word": "GEHEIM",
            "email": "GEHEIM",
            "token": "GEHEIM",
        }
    )
    assert cleaned == {"type": "konkret"}


def test_feed_filters_and_soft_delete(client):
    clubroom, anna, _ = make_room()
    client.force_login(anna)
    event = FeedEvent.objects.filter(event_type="clubroom.created").get()
    response = client.get(reverse("feed:index"), {"typ": event.event_type})
    assert response.status_code == 200
    assert "Clubraum gegründet" in response.content.decode()

    response = client.post(reverse("feed:remove", kwargs={"pk": event.pk}))
    assert response.status_code == 302
    event.refresh_from_db()
    assert event.deleted_at is not None
    assert event.metadata == {}
    content = client.get(reverse("feed:index")).content.decode()
    assert "Eintrag entfernt" in content


def test_feed_permissions(client):
    clubroom, anna, _ = make_room()
    guest = User.objects.create_user(
        username="gast", email="gast@example.com", password="sehr-geheim-1234"
    )
    moderator = User.objects.create_user(
        username="mod", email="mod@example.com", password="sehr-geheim-1234"
    )
    Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    Membership.objects.create(clubroom=clubroom, user=moderator, role=MODERATOR)

    client.force_login(guest)
    assert client.get(reverse("feed:index")).status_code == 403
    client.force_login(moderator)
    assert client.get(reverse("feed:index")).status_code == 200
    assert client.get(reverse("lounge:index")).status_code == 200


def test_moderator_sees_status_but_no_secret_answers(client):
    clubroom, anna, bea = make_room()
    moderator = User.objects.create_user(
        username="mod", email="mod@example.com", password="sehr-geheim-1234"
    )
    Membership.objects.create(clubroom=clubroom, user=moderator, role=MODERATOR)
    create_check_in(clubroom=clubroom, user=anna, mood=4, energy=4, closeness=4)
    client.force_login(moderator)
    content = client.get(reverse("lounge:index")).content.decode()
    assert "3-Tage-Barometer" in content
    assert "Stimmung 4/5" not in content


def test_safe_mode_service_is_idempotent():
    clubroom, anna, bea = make_room()
    assert set_safe_mode(user=bea, active=True) == 0
    assert set_safe_mode(user=bea, active=True) == 0
    record_event(
        clubroom=clubroom,
        event_type=EVENT_CHECKIN_CREATED,
        actor=anna,
    )
    assert Notification.objects.filter(user=bea, delivered_at__isnull=True).count() == 1
    assert set_safe_mode(user=bea, active=False) == 1
    assert set_safe_mode(user=bea, active=False) == 0
