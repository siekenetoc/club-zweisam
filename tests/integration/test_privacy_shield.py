import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.clubroom.models import Membership
from apps.clubroom.permissions import GUEST, OWNER
from apps.clubroom.services import create_clubroom
from apps.feed.models import FeedEvent, Notification
from apps.lounge.services import create_check_in
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


def test_sync_requires_login_and_membership(client):
    assert client.post(reverse("lounge:safe_mode_sync"), {"active": "1"}).status_code == 302
    outsider = User.objects.create_user(
        username="out", email="out@example.com", password="sehr-geheim-1234"
    )
    client.force_login(outsider)
    assert client.post(reverse("lounge:safe_mode_sync"), {"active": "1"}).status_code == 403


def test_activation_is_private_and_queues_notifications(client):
    clubroom, anna, bea = make_room()
    client.force_login(bea)
    before_events = FeedEvent.objects.count()
    response = client.post(reverse("lounge:safe_mode_sync"), {"active": "1"})
    assert response.status_code == 200
    assert response.json() == {"active": True, "delivered": 0}
    bea.refresh_from_db()
    assert bea.is_safe_mode_active is True
    assert FeedEvent.objects.count() == before_events
    assert Notification.objects.count() == 0

    create_wish(
        clubroom=clubroom,
        user=anna,
        wish_type="offen",
        title="Sichtbar",
        body="Inhalt",
    )
    queued = Notification.objects.get(user=bea)
    assert queued.delivered_at is None
    assert FeedEvent.objects.filter(actor=bea).count() == 0

    response = client.post(reverse("lounge:safe_mode_sync"), {"active": "0"})
    assert response.status_code == 200
    assert response.json()["active"] is False
    assert response.json()["delivered"] == 1
    queued.refresh_from_db()
    assert queued.delivered_at is not None


def test_admin_cannot_see_safe_mode_flag(client):
    clubroom, anna, _ = make_room()
    create_check_in(clubroom=clubroom, user=anna, mood=3, energy=3, closeness=3)
    anna.is_safe_mode_active = True
    anna.save(update_fields=["is_safe_mode_active"])
    superuser = User.objects.create_superuser(
        username="root", email="root@example.com", password="sehr-geheim-1234"
    )
    client.force_login(superuser)
    content = client.get(reverse("admin:accounts_user_change", args=[anna.pk])).content.decode()
    assert "is_safe_mode_active" not in content
    assert "Safe-Mode" not in content


def test_decoy_is_local_and_has_no_external_assets(client):
    content = client.get(reverse("clubroom:home")).content.decode()
    assert 'id="privacy-shield"' in content
    assert "Notizen" in content
    assert "shield-activate" in content
    assert "http://" not in content
    assert "https://" not in content


def test_guest_can_use_privacy_shield(client):
    clubroom, anna, _ = make_room()
    guest = User.objects.create_user(
        username="gast", email="gast@example.com", password="sehr-geheim-1234"
    )
    Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    client.force_login(guest)
    response = client.post(reverse("lounge:safe_mode_sync"), {"active": "1"})
    assert response.status_code == 200
    guest.refresh_from_db()
    assert guest.is_safe_mode_active is True
