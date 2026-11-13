import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.urls import reverse

from apps.accounts.models import User
from apps.clubroom.models import Membership
from apps.clubroom.permissions import GUEST, OWNER
from apps.clubroom.services import create_clubroom
from apps.vitrine.models import Commonality
from apps.wishes.models import (
    ACTION_ACCEPT,
    ACTION_ALTERNATIVE,
    ACTION_BOUNDARY,
    ACTION_PARTIAL,
    ACTION_POSTPONE,
    ACTION_REJECT,
    ACTION_TALK,
    STATUS_AGREED,
    STATUS_BOUNDARY,
    STATUS_CONFIRMED,
    STATUS_DRAFT,
    STATUS_PENDING,
    STATUS_PLACED,
    STATUS_POSTPONED,
    STATUS_REJECTED,
    STATUS_REPLIED,
    Wish,
    WishResponse,
)
from apps.wishes.services import (
    confirm_fulfilled,
    create_wish,
    mark_fulfilled,
    requester_decide,
    respond_to_wish,
    share_wish,
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


def new_wish(clubroom, anna, **overrides):
    data = {
        "clubroom": clubroom,
        "user": anna,
        "wish_type": "konkret",
        "title": "Ein Abend ohne Handy",
        "body": "Wollen wir einen Abend ohne Handy verbringen?",
        "category": "Alltag",
        "intensity": 1,
        "timeframe": "woche",
    }
    data.update(overrides)
    return create_wish(**data)


def test_create_wish_is_placed_and_encrypted_at_rest():
    clubroom, anna, _ = make_room()
    wish = new_wish(clubroom, anna)
    assert wish.status == STATUS_PLACED
    assert wish.is_private is False
    with connection.cursor() as cursor:
        cursor.execute("SELECT body FROM wishes_wish WHERE id = %s", [wish.pk])
        stored = cursor.fetchone()[0]
    assert stored.startswith("enc:v1:")
    assert "Handy" not in stored


def test_private_wish_is_only_visible_to_creator(client):
    clubroom, anna, bea = make_room()
    wish = new_wish(clubroom, anna, is_private=True)
    assert wish.status == STATUS_DRAFT

    client.force_login(anna)
    assert client.get(reverse("wishes:detail", kwargs={"pk": wish.pk})).status_code == 200
    client.force_login(bea)
    assert client.get(reverse("wishes:detail", kwargs={"pk": wish.pk})).status_code == 403

    share_wish(wish=wish, user=anna)
    wish.refresh_from_db()
    assert wish.is_private is False
    assert wish.status == STATUS_PLACED
    client.force_login(bea)
    assert client.get(reverse("wishes:detail", kwargs={"pk": wish.pk})).status_code == 200


def test_accept_fulfill_confirm_flow_creates_commonality():
    clubroom, anna, bea = make_room()
    wish = new_wish(clubroom, anna)
    respond_to_wish(wish=wish, user=bea, action=ACTION_ACCEPT)
    wish.refresh_from_db()
    assert wish.status == STATUS_AGREED
    assert wish.agreed_at is not None

    mark_fulfilled(wish=wish, user=anna)
    wish.refresh_from_db()
    assert wish.status == STATUS_PENDING
    with pytest.raises(ValidationError):
        confirm_fulfilled(wish=wish, user=anna)

    confirm_fulfilled(wish=wish, user=bea)
    wish.refresh_from_db()
    assert wish.status == STATUS_CONFIRMED
    assert wish.confirmed_at is not None
    assert Commonality.objects.filter(source_type="wish", source_id=wish.pk).exists()


def test_alternative_requires_note_and_requester_decision():
    clubroom, anna, bea = make_room()
    wish = new_wish(clubroom, anna)
    with pytest.raises(ValidationError):
        respond_to_wish(wish=wish, user=bea, action=ACTION_ALTERNATIVE, note="")

    respond_to_wish(
        wish=wish,
        user=bea,
        action=ACTION_ALTERNATIVE,
        note="Lieber am Wochenende.",
    )
    wish.refresh_from_db()
    assert wish.status == STATUS_REPLIED

    requester_decide(wish=wish, user=anna, accept=True)
    wish.refresh_from_db()
    assert wish.status == STATUS_AGREED


def test_partial_response_requires_note_and_can_be_declined():
    clubroom, anna, bea = make_room()
    wish = new_wish(clubroom, anna)
    with pytest.raises(ValidationError):
        respond_to_wish(wish=wish, user=bea, action=ACTION_PARTIAL, note="")
    respond_to_wish(wish=wish, user=bea, action=ACTION_PARTIAL, note="Nur teilweise.")
    requester_decide(wish=wish, user=anna, accept=False)
    wish.refresh_from_db()
    assert wish.status == STATUS_REJECTED


def test_reject_postpone_boundary_and_talk_are_neutral():
    clubroom, anna, bea = make_room()

    wish = new_wish(clubroom, anna, title="A")
    respond_to_wish(wish=wish, user=bea, action=ACTION_REJECT, note="Nicht heute.")
    wish.refresh_from_db()
    assert wish.status == STATUS_REJECTED

    wish = new_wish(clubroom, anna, title="B")
    respond_to_wish(wish=wish, user=bea, action=ACTION_POSTPONE)
    wish.refresh_from_db()
    assert wish.status == STATUS_POSTPONED

    wish = new_wish(clubroom, anna, title="C")
    respond_to_wish(wish=wish, user=bea, action=ACTION_BOUNDARY, note="Das ist meine Grenze.")
    wish.refresh_from_db()
    assert wish.status == STATUS_BOUNDARY

    wish = new_wish(clubroom, anna, title="D")
    respond_to_wish(wish=wish, user=bea, action=ACTION_TALK, note="Erst sprechen.")
    wish.refresh_from_db()
    assert wish.status == STATUS_POSTPONED


def test_no_chained_or_duplicate_wishes(client):
    clubroom, anna, bea = make_room()
    wish = new_wish(clubroom, anna)
    respond_to_wish(wish=wish, user=bea, action=ACTION_ACCEPT)
    with pytest.raises(ValidationError):
        respond_to_wish(wish=wish, user=bea, action=ACTION_ALTERNATIVE, note="Doch anders.")
    with pytest.raises(ValidationError):
        respond_to_wish(wish=wish, user=anna, action=ACTION_ACCEPT)
    assert WishResponse.objects.filter(wish=wish).count() == 1
    assert Wish.objects.count() == 1


def test_boundary_note_is_not_rendered(client):
    clubroom, anna, bea = make_room()
    wish = new_wish(clubroom, anna)
    respond_to_wish(wish=wish, user=bea, action=ACTION_BOUNDARY, note="Geheime Begründung")
    client.force_login(anna)
    content = client.get(reverse("wishes:detail", kwargs={"pk": wish.pk})).content.decode()
    assert "Grenze respektiert" in content
    assert "Geheime Begründung" not in content


def test_wish_notes_are_encrypted_at_rest():
    clubroom, anna, bea = make_room()
    wish = new_wish(clubroom, anna)
    respond_to_wish(wish=wish, user=bea, action=ACTION_ALTERNATIVE, note="Nur am Wochenende.")
    with connection.cursor() as cursor:
        cursor.execute("SELECT note FROM wishes_wishresponse WHERE wish_id = %s", [wish.pk])
        stored = cursor.fetchone()[0]
    assert stored.startswith("enc:v1:")
    assert "Wochenende" not in stored


def test_non_owner_has_no_concierge_access(client):
    clubroom, anna, bea = make_room()
    guest = User.objects.create_user(
        username="gast", email="gast@example.com", password="sehr-geheim-1234"
    )
    Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    client.force_login(guest)
    assert client.get(reverse("wishes:index")).status_code == 403
