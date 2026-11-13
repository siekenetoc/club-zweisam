from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.clubroom.models import Membership
from apps.clubroom.permissions import GUEST, OWNER
from apps.clubroom.services import create_clubroom
from apps.roulette.models import (
    RESULT_FULL,
    RESULT_NONE,
    RESULT_PARTIAL,
    Deck,
    Match,
    SecretAnswer,
)
from apps.roulette.services import (
    both_owners_opted_in,
    opt_in,
    purge_expired_answers,
    release_match,
    start_round,
    submit_answer,
)
from apps.vitrine.models import Commonality

pytestmark = pytest.mark.django_db


def make_two_owners():
    anna = User.objects.create_user(
        username="anna", email="anna@example.com", password="sehr-geheim-1234"
    )
    bea = User.objects.create_user(
        username="bea", email="bea@example.com", password="sehr-geheim-1234"
    )
    clubroom = create_clubroom(user=anna, name="Unser Raum", safe_word="Anker")
    Membership.objects.create(clubroom=clubroom, user=bea, role=OWNER)
    return clubroom, anna, bea


def start_deck(clubroom, user, code="A"):
    return start_round(clubroom=clubroom, deck=Deck.objects.get(code=code), user=user)


def answer(round_obj, user, code="A", order=1, value="ja", boundary=False):
    question = round_obj.deck.questions.get(order=order)
    return submit_answer(
        round_obj=round_obj,
        question=question,
        user=user,
        answer=value,
        is_boundary=boundary,
    )


def test_seed_contains_four_decks_and_forty_questions():
    assert Deck.objects.count() == 4
    assert sum(deck.questions.count() for deck in Deck.objects.all()) == 40
    assert Deck.objects.get(code="D").requires_opt_in is True
    assert Deck.objects.get(code="A").requires_opt_in is False


def test_deck_d_requires_opt_in_from_both():
    clubroom, anna, bea = make_two_owners()
    deck = Deck.objects.get(code="D")
    opt_in(clubroom=clubroom, deck=deck, user=anna)
    assert both_owners_opted_in(clubroom, deck) is False
    with pytest.raises(ValidationError):
        start_round(clubroom=clubroom, deck=deck, user=anna)

    opt_in(clubroom=clubroom, deck=deck, user=bea)
    assert both_owners_opted_in(clubroom, deck) is True
    round_obj = start_round(clubroom=clubroom, deck=deck, user=anna)
    assert round_obj.deck == deck


def test_answer_is_encrypted_at_rest():
    clubroom, anna, bea = make_two_owners()
    round_obj = start_deck(clubroom, anna)
    answer(round_obj, anna, value="ja")
    with connection.cursor() as cursor:
        cursor.execute("SELECT answer FROM roulette_secretanswer WHERE user_id = %s", [anna.id])
        stored = cursor.fetchone()[0]
    assert stored.startswith("enc:v1:")
    assert "ja" != stored
    assert SecretAnswer.objects.get(user=anna).answer == "ja"


def test_partial_match_is_symmetric_after_release(client):
    clubroom, anna, bea = make_two_owners()
    round_obj = start_deck(clubroom, anna)
    answer(round_obj, anna, value="ja")
    answer(round_obj, bea, value="vielleicht")
    match = Match.objects.get(round=round_obj)
    assert match.result == RESULT_PARTIAL
    assert match.released_at is None

    client.force_login(anna)
    before_url = reverse("roulette:round", kwargs={"pk": round_obj.pk})
    before_response = client.get(before_url)
    before_state = next(
        state for state in before_response.context["states"] if state["question"].order == 1
    )
    assert before_state["partner_label"] is None
    assert before_state["result_label"] is None

    release_match(match=match, user=anna)
    assert Commonality.objects.count() == 0
    release_match(match=match, user=bea)
    match.refresh_from_db()
    assert match.released_at is not None
    assert Commonality.objects.count() == 1

    client.force_login(anna)
    anna_state = next(
        state for state in client.get(before_url).context["states"] if state["question"].order == 1
    )
    client.force_login(bea)
    bea_state = next(
        state for state in client.get(before_url).context["states"] if state["question"].order == 1
    )
    for state in (anna_state, bea_state):
        assert state["result_label"] == "Teilweiser Match"
        assert {state["own_label"], state["partner_label"]} == {"Ja", "Vielleicht"}
    assert anna_state["own_label"] == "Ja"
    assert bea_state["own_label"] == "Vielleicht"


def test_full_match_creates_commonality_in_vitrine(client):
    clubroom, anna, bea = make_two_owners()
    round_obj = start_deck(clubroom, anna)
    answer(round_obj, anna, value="ja")
    answer(round_obj, bea, value="ja")
    match = Match.objects.get(round=round_obj)
    assert match.result == RESULT_FULL
    release_match(match=match, user=anna)
    release_match(match=match, user=bea)

    client.force_login(anna)
    response = client.get(reverse("vitrine:index"))
    content = response.content.decode()
    assert response.status_code == 200
    assert round_obj.deck.questions.get(order=1).text in content
    assert "Vollständiger Match" in content
    assert "Deine Antwort" not in content


def test_boundary_is_respected_and_never_revealed(client):
    clubroom, anna, bea = make_two_owners()
    round_obj = start_deck(clubroom, anna)
    answer(round_obj, anna, value="ja", boundary=True)
    answer(round_obj, bea, value="ja")
    match = Match.objects.get(round=round_obj)
    assert match.result == RESULT_NONE
    assert match.has_boundary is True

    release_match(match=match, user=anna)
    release_match(match=match, user=bea)
    client.force_login(bea)
    content = client.get(reverse("roulette:round", kwargs={"pk": round_obj.pk})).content.decode()
    assert "Grenze respektiert" in content
    assert "Kein Match" in content
    assert ">Ja<" not in content
    assert Commonality.objects.count() == 0


def test_no_match_leaks_nothing_after_release(client):
    clubroom, anna, bea = make_two_owners()
    round_obj = start_deck(clubroom, anna)
    answer(round_obj, anna, value="nein")
    answer(round_obj, bea, value="ja")
    match = Match.objects.get(round=round_obj)
    assert match.result == RESULT_NONE
    release_match(match=match, user=anna)
    release_match(match=match, user=bea)

    client.force_login(bea)
    content = client.get(reverse("roulette:round", kwargs={"pk": round_obj.pk})).content.decode()
    assert "Kein Match" in content
    assert "Deine Antwort" not in content
    assert "Antwort von" not in content
    assert Commonality.objects.count() == 0


def test_release_by_one_keeps_content_hidden(client):
    clubroom, anna, bea = make_two_owners()
    round_obj = start_deck(clubroom, anna)
    answer(round_obj, anna, value="ja")
    answer(round_obj, bea, value="vielleicht")
    match = Match.objects.get(round=round_obj)
    release_match(match=match, user=anna)

    client.force_login(anna)
    response = client.get(reverse("roulette:round", kwargs={"pk": round_obj.pk}))
    state = next(state for state in response.context["states"] if state["question"].order == 1)
    assert state["result_label"] is None
    assert state["partner_label"] is None
    assert state["own_released"] is True


def test_duplicate_and_invalid_answers_are_rejected():
    clubroom, anna, bea = make_two_owners()
    round_obj = start_deck(clubroom, anna)
    answer(round_obj, anna, value="ja")
    with pytest.raises(ValidationError):
        answer(round_obj, anna, value="nein")
    with pytest.raises(ValidationError):
        answer(round_obj, bea, value="unsinn")
    other_question = Deck.objects.get(code="B").questions.get(order=1)
    with pytest.raises(ValidationError):
        submit_answer(
            round_obj=round_obj,
            question=other_question,
            user=bea,
            answer="ja",
            is_boundary=False,
        )


def test_non_owner_cannot_access_roulette_or_vitrine(client):
    clubroom, anna, bea = make_two_owners()
    guest = User.objects.create_user(
        username="gast", email="gast@example.com", password="sehr-geheim-1234"
    )
    Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    client.force_login(guest)
    assert client.get(reverse("roulette:index")).status_code == 403
    assert client.get(reverse("vitrine:index")).status_code == 403


def test_round_end_deletes_answers_but_keeps_match_and_commonality():
    clubroom, anna, bea = make_two_owners()
    round_obj = start_deck(clubroom, anna)
    answer(round_obj, anna, value="ja")
    answer(round_obj, bea, value="ja")
    match = Match.objects.get(round=round_obj)
    release_match(match=match, user=anna)
    release_match(match=match, user=bea)

    from apps.roulette.services import end_round

    end_round(round_obj=round_obj, user=anna)
    round_obj.refresh_from_db()
    assert round_obj.ended_at is not None
    for secret in SecretAnswer.objects.filter(round=round_obj):
        assert secret.answer == ""
        assert secret.deleted_at is not None
    assert Match.objects.filter(pk=match.pk).exists()
    assert Commonality.objects.count() == 1


def test_purge_removes_old_answers_and_non_matches():
    clubroom, anna, bea = make_two_owners()
    round_obj = start_deck(clubroom, anna)
    answer(round_obj, anna, value="nein", order=1)
    answer(round_obj, bea, value="ja", order=1)
    none_match = Match.objects.get(round=round_obj)

    answer(round_obj, anna, value="ja", order=2)
    answer(round_obj, bea, value="ja", order=2)
    full_match = Match.objects.get(round=round_obj, question__order=2)

    old = timezone.now() - timedelta(days=31)
    SecretAnswer.objects.update(created_at=old)
    Match.objects.update(created_at=old)

    result = purge_expired_answers()
    assert result == {"cleared_answers": 4, "deleted_non_matches": 1}
    assert not Match.objects.filter(pk=none_match.pk).exists()
    assert Match.objects.filter(pk=full_match.pk).exists()
    assert all(
        secret.answer == "" and secret.deleted_at is not None
        for secret in SecretAnswer.objects.all()
    )
