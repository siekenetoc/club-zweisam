import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.accounts.models import User
from apps.clubroom.models import Membership
from apps.clubroom.permissions import GUEST, OWNER
from apps.clubroom.services import create_clubroom
from apps.playbook.models import CATEGORY_CHOICES, Challenge
from apps.playbook.services import (
    abort_run,
    active_run_for,
    both_owners_opted_in_stage3,
    confirm_run,
    daily_run_count,
    opt_in_stage3,
    revoke_opt_in_stage3,
    start_challenge,
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


def challenge(stage=1):
    return Challenge.objects.filter(consent_stage=stage).first()


def test_seed_has_library_with_stage_three():
    assert Challenge.objects.count() == 16
    assert len({challenge.category for challenge in Challenge.objects.all()}) == len(
        CATEGORY_CHOICES
    )
    assert Challenge.objects.filter(consent_stage=3).exists()


def test_stage_one_can_start_without_opt_in():
    clubroom, anna, _ = make_room()
    run = start_challenge(clubroom=clubroom, challenge=challenge(stage=1), user=anna)
    assert run.is_active
    assert active_run_for(clubroom) == run


def test_stage_three_requires_both_opt_ins():
    clubroom, anna, bea = make_room()
    stage3 = challenge(stage=3)
    with pytest.raises(ValidationError):
        start_challenge(clubroom=clubroom, challenge=stage3, user=anna)

    opt_in_stage3(clubroom=clubroom, user=anna)
    assert both_owners_opted_in_stage3(clubroom) is False
    with pytest.raises(ValidationError):
        start_challenge(clubroom=clubroom, challenge=stage3, user=anna)

    opt_in_stage3(clubroom=clubroom, user=bea)
    assert both_owners_opted_in_stage3(clubroom) is True
    run = start_challenge(clubroom=clubroom, challenge=stage3, user=anna)
    assert run.challenge == stage3


def test_opt_in_can_be_revoked():
    clubroom, anna, bea = make_room()
    opt_in_stage3(clubroom=clubroom, user=anna)
    opt_in_stage3(clubroom=clubroom, user=bea)
    revoke_opt_in_stage3(clubroom=clubroom, user=bea)
    assert both_owners_opted_in_stage3(clubroom) is False


def test_daily_limit_blocks_fourth_challenge():
    clubroom, anna, _ = make_room()
    for _ in range(3):
        run = start_challenge(clubroom=clubroom, challenge=challenge(stage=1), user=anna)
        abort_run(run=run, user=anna)
    assert daily_run_count(clubroom) == 3
    with pytest.raises(ValidationError):
        start_challenge(clubroom=clubroom, challenge=challenge(stage=1), user=anna)


def test_only_one_active_run():
    clubroom, anna, _ = make_room()
    start_challenge(clubroom=clubroom, challenge=challenge(stage=1), user=anna)
    with pytest.raises(ValidationError):
        start_challenge(clubroom=clubroom, challenge=challenge(stage=1), user=anna)


def test_both_confirmations_complete_run():
    clubroom, anna, bea = make_room()
    run = start_challenge(clubroom=clubroom, challenge=challenge(stage=1), user=anna)
    confirm_run(run=run, user=anna)
    run.refresh_from_db()
    assert run.is_completed is False
    assert run.confirmed_by_a is True

    confirm_run(run=run, user=bea)
    run.refresh_from_db()
    assert run.is_completed is True
    assert run.completed_at is not None
    with pytest.raises(ValidationError):
        confirm_run(run=run, user=bea)


def test_abort_is_immediate_and_final():
    clubroom, anna, bea = make_room()
    run = start_challenge(clubroom=clubroom, challenge=challenge(stage=1), user=anna)
    abort_run(run=run, user=bea)
    run.refresh_from_db()
    assert run.is_aborted
    assert run.aborted_by == bea
    with pytest.raises(ValidationError):
        confirm_run(run=run, user=anna)
    with pytest.raises(ValidationError):
        abort_run(run=run, user=anna)


def test_non_owner_cannot_start_challenge(client):
    clubroom, anna, _ = make_room()
    guest = User.objects.create_user(
        username="gast", email="gast@example.com", password="sehr-geheim-1234"
    )
    Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    with pytest.raises(ValidationError):
        start_challenge(clubroom=clubroom, challenge=challenge(stage=1), user=guest)
    client.force_login(guest)
    assert client.get(reverse("playbook:index")).status_code == 403


def test_pages_render_for_owner(client):
    clubroom, anna, _ = make_room()
    client.force_login(anna)
    assert client.get(reverse("playbook:index")).status_code == 200
    run = start_challenge(clubroom=clubroom, challenge=challenge(stage=1), user=anna)
    response = client.get(reverse("playbook:run", kwargs={"pk": run.pk}))
    assert response.status_code == 200
    assert "challengeTimer" in response.content.decode()
