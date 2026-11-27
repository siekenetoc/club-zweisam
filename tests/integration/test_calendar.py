import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.calendar.models import CalendarEntry, CalendarFeedToken
from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER
from apps.clubroom.services import create_clubroom

pytestmark = pytest.mark.django_db


def make_room():
    owner = User.objects.create_user(
        username="kalender", email="kalender@example.com", password="sehr-geheim-1234"
    )
    partner = User.objects.create_user(
        username="kalender2", email="kalender2@example.com", password="sehr-geheim-1234"
    )
    clubroom = create_clubroom(user=owner, name="Kalenderraum", safe_word="Anker")
    Membership.objects.create(clubroom=clubroom, user=partner, role=OWNER)
    return clubroom, owner, partner


def test_calendar_is_wired_for_owner(client):
    clubroom, owner, partner = make_room()
    client.force_login(owner)
    response = client.get(reverse("calendar:index"))
    assert response.status_code == 200
    assert "Kalender" in response.content.decode()
    client.force_login(partner)
    assert client.get(reverse("calendar:index")).status_code == 200


def test_calendar_ics_feed_and_token_revocation(client):
    from apps.calendar.models import CalendarEntry

    clubroom, owner, _ = make_room()
    CalendarEntry.objects.create(
        clubroom=clubroom,
        created_by=owner,
        kind="event",
        title="Candlelight",
        description="Nur wir",
        start_at=timezone.now(),
        all_day=False,
    )
    token, raw = CalendarFeedToken.issue(clubroom=clubroom, user=owner)
    response = client.get(reverse("calendar:feed", kwargs={"token": raw}))
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/calendar")
    assert "Candlelight" in response.content.decode()
    assert "Nur wir" not in response.content.decode()
    CalendarFeedToken.objects.filter(pk=token.pk).update(revoked_at=timezone.now())
    assert client.get(reverse("calendar:feed", kwargs={"token": raw})).status_code == 404


def test_calendar_views_and_date_prefill(client):
    clubroom, owner, _ = make_room()
    client.force_login(owner)
    for view in ("tag", "woche", "monat", "agenda"):
        response = client.get(reverse("calendar:index"), {"ansicht": view, "datum": "2026-12-04"})
        assert response.status_code == 200
    response = client.get(reverse("calendar:index"), {"ansicht": "tag", "datum": "2026-12-04"})
    assert response.context["form"].initial["start_at"].date().isoformat() == "2026-12-04"


def test_datenight_accept_creates_calendar_entry(client):
    from apps.calendar.models import DateNight

    clubroom, owner, partner = make_room()
    night = DateNight.objects.create(
        clubroom=clubroom,
        proposed_by=owner,
        scheduled_for=timezone.now() + timezone.timedelta(days=3),
        motto="Kerzen und Tee",
    )
    client.force_login(partner)
    response = client.post(
        reverse("datenight:respond", kwargs={"pk": night.pk}), {"action": "accept"}
    )
    assert response.status_code == 302
    night.refresh_from_db()
    assert night.status == "accepted"
    assert CalendarEntry.objects.filter(clubroom=clubroom, title__contains="Kerzen").exists()


def test_calendar_create_and_task_toggle(client):
    clubroom, owner, _ = make_room()
    client.force_login(owner)
    response = client.post(
        reverse("calendar:index"),
        {
            "kind": "task",
            "title": "Blumen",
            "description": "",
            "start_at": "2026-11-28T10:00",
            "end_at": "",
            "all_day": "",
        },
    )
    assert response.status_code == 302
    entry = CalendarEntry.objects.get(clubroom=clubroom)
    assert entry.title == "Blumen"
    client.post(reverse("calendar:toggle_task", kwargs={"pk": entry.pk}))
    entry.refresh_from_db()
    assert entry.is_done is True
