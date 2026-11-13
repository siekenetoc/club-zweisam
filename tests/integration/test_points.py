import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.accounts.models import User
from apps.clubroom.models import Membership
from apps.clubroom.permissions import GUEST, OWNER
from apps.clubroom.services import create_clubroom
from apps.feed.models import FeedEvent
from apps.playbook.models import Challenge
from apps.playbook.services import confirm_run, start_challenge
from apps.points.models import (
    REASON_CHALLENGE,
    REASON_WISH,
    SCOPE_DYAD,
    SCOPE_GUEST,
    Entry,
    Ledger,
    Redemption,
    Reward,
)
from apps.points.services import (
    accept_redemption,
    award_points,
    cancel_redemption,
    complete_redemption,
    confirm_refund,
    decline_redemption,
    get_or_create_ledger,
    grant_recognition,
    request_redemption,
    request_refund,
)
from apps.wishes.models import ACTION_ACCEPT, ACTION_BOUNDARY, ACTION_REJECT
from apps.wishes.services import (
    confirm_fulfilled,
    create_wish,
    mark_fulfilled,
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


def balance(clubroom, user):
    return get_or_create_ledger(clubroom, user).balance


def test_reward_catalog_seed():
    assert Reward.objects.count() == 10
    assert Reward.objects.values("category").distinct().count() == 5
    assert Reward.objects.filter(category="erotisch").exists()


def test_ledger_scopes_are_separate():
    clubroom, anna, bea = make_room()
    guest = User.objects.create_user(
        username="gast", email="gast@example.com", password="sehr-geheim-1234"
    )
    Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    assert get_or_create_ledger(clubroom, anna).scope == SCOPE_DYAD
    assert get_or_create_ledger(clubroom, guest).scope == SCOPE_GUEST


def test_guest_ledger_is_isolated_and_read_only(client):
    clubroom, anna, bea = make_room()
    guest = User.objects.create_user(
        username="gast", email="gast@example.com", password="sehr-geheim-1234"
    )
    Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    grant_recognition(clubroom=clubroom, guest_user=guest, actor=anna, amount=2)
    guest_ledger = get_or_create_ledger(clubroom, guest)
    assert guest_ledger.balance == 2
    assert guest_ledger.scope == SCOPE_GUEST
    assert Ledger.objects.filter(clubroom=clubroom, scope=SCOPE_DYAD).count() == 0

    client.force_login(guest)
    assert client.get(reverse("points:index")).status_code == 403
    response = client.get(reverse("points:my"))
    assert response.status_code == 200
    assert "Gast-Konto ist isoliert" in response.content.decode()
    assert str(2) in response.content.decode()


def test_challenge_awards_both_owners_once():
    clubroom, anna, bea = make_room()
    challenge = Challenge.objects.filter(consent_stage=1).first()
    run = start_challenge(clubroom=clubroom, challenge=challenge, user=anna)
    confirm_run(run=run, user=anna)
    confirm_run(run=run, user=bea)
    assert balance(clubroom, anna) == challenge.points
    assert balance(clubroom, bea) == challenge.points
    assert Entry.objects.filter(reason=REASON_CHALLENGE).count() == 2


def test_wish_confirmation_awards_responder_only():
    clubroom, anna, bea = make_room()
    wish = create_wish(
        clubroom=clubroom,
        user=anna,
        wish_type="konkret",
        title="Kaffee",
        body="Kaffee ans Bett?",
    )
    respond_to_wish(wish=wish, user=bea, action=ACTION_ACCEPT)
    mark_fulfilled(wish=wish, user=anna)
    confirm_fulfilled(wish=wish, user=bea)
    assert balance(clubroom, bea) == 1
    assert balance(clubroom, anna) == 0
    assert Entry.objects.filter(reason=REASON_WISH).exists()


def test_rejection_and_boundary_never_deduct_points():
    clubroom, anna, bea = make_room()
    award_points(clubroom=clubroom, user=bea, amount=2, reason=REASON_WISH, actor=anna)
    for action in (ACTION_REJECT, ACTION_BOUNDARY):
        wish = create_wish(
            clubroom=clubroom,
            user=anna,
            wish_type="offen",
            title=f"Wunsch {action}",
            body="Inhalt",
        )
        respond_to_wish(wish=wish, user=bea, action=action)
        assert balance(clubroom, bea) == 2


def test_daily_caps_for_awards():
    clubroom, anna, _ = make_room()
    assert (
        award_points(
            clubroom=clubroom,
            user=anna,
            amount=2,
            reason=REASON_CHALLENGE,
            challenge=True,
        ).delta
        == 2
    )
    assert (
        award_points(
            clubroom=clubroom,
            user=anna,
            amount=2,
            reason=REASON_CHALLENGE,
            challenge=True,
        ).delta
        == 1
    )
    assert (
        award_points(
            clubroom=clubroom,
            user=anna,
            amount=2,
            reason=REASON_CHALLENGE,
            challenge=True,
        )
        is None
    )
    for _ in range(8):
        award_points(clubroom=clubroom, user=anna, amount=1, reason=REASON_WISH, actor=anna)
    assert balance(clubroom, anna) == 10
    assert (
        award_points(clubroom=clubroom, user=anna, amount=1, reason=REASON_WISH, actor=anna) is None
    )


def test_redemption_flow_deducts_only_on_acceptance():
    clubroom, anna, bea = make_room()
    reward = Reward.objects.get(cost=2)
    award_points(clubroom=clubroom, user=anna, amount=5, reason=REASON_WISH, actor=bea)
    redemption = request_redemption(clubroom=clubroom, user=anna, reward=reward)
    assert balance(clubroom, anna) == 5

    accept_redemption(redemption=redemption, user=bea)
    assert balance(clubroom, anna) == 3
    redemption.refresh_from_db()
    assert redemption.status == "accepted"
    assert redemption.accepted_by == bea
    assert redemption.requested_by == anna
    with pytest.raises(ValidationError):
        accept_redemption(redemption=redemption, user=anna)

    complete_redemption(redemption=redemption, user=anna)
    redemption.refresh_from_db()
    assert redemption.status == "completed"


def test_decline_and_cancel_do_not_deduct():
    clubroom, anna, bea = make_room()
    reward = Reward.objects.get(cost=2)
    award_points(clubroom=clubroom, user=anna, amount=5, reason=REASON_WISH, actor=bea)
    redemption = request_redemption(clubroom=clubroom, user=anna, reward=reward)
    decline_redemption(redemption=redemption, user=bea)
    assert balance(clubroom, anna) == 5

    redemption = request_redemption(clubroom=clubroom, user=anna, reward=reward)
    cancel_redemption(redemption=redemption, user=anna)
    assert balance(clubroom, anna) == 5


def test_insufficient_points_blocks_request():
    clubroom, anna, _ = make_room()
    reward = Reward.objects.get(cost=2)
    with pytest.raises(ValidationError):
        request_redemption(clubroom=clubroom, user=anna, reward=reward)
    assert Redemption.objects.count() == 0


def test_refund_requires_both_sides():
    clubroom, anna, bea = make_room()
    reward = Reward.objects.get(cost=2)
    award_points(clubroom=clubroom, user=anna, amount=5, reason=REASON_WISH, actor=bea)
    redemption = request_redemption(clubroom=clubroom, user=anna, reward=reward)
    accept_redemption(redemption=redemption, user=bea)
    assert balance(clubroom, anna) == 3

    request_refund(redemption=redemption, user=anna)
    with pytest.raises(ValidationError):
        confirm_refund(redemption=redemption, user=anna)
    confirm_refund(redemption=redemption, user=bea)
    assert balance(clubroom, anna) == 5
    redemption.refresh_from_db()
    assert redemption.status == "refunded"
    assert redemption.refund_confirmed_by == bea
    with pytest.raises(ValidationError):
        confirm_refund(redemption=redemption, user=bea)


def test_guest_cannot_earn_dyad_points_or_use_points_index(client):
    clubroom, anna, _ = make_room()
    guest = User.objects.create_user(
        username="gast", email="gast@example.com", password="sehr-geheim-1234"
    )
    Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    with pytest.raises(ValidationError):
        award_points(
            clubroom=clubroom,
            user=guest,
            amount=1,
            reason=REASON_WISH,
            actor=anna,
        )
    client.force_login(guest)
    assert client.get(reverse("points:index")).status_code == 403


def test_points_do_not_create_feed_events():
    clubroom, anna, bea = make_room()
    before = FeedEvent.objects.count()
    award_points(clubroom=clubroom, user=anna, amount=2, reason=REASON_WISH, actor=bea)
    assert FeedEvent.objects.count() == before


def test_owner_points_page_renders(client):
    clubroom, anna, _ = make_room()
    client.force_login(anna)
    response = client.get(reverse("points:index"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Belohnungen" in content
    assert "Gast-Ledger" in content
    assert "Frühstück ans Bett" in content
