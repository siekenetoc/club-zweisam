from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER
from apps.roulette.forms import AnswerForm
from apps.roulette.models import (
    ANSWER_LABELS,
    RESULT_NONE,
    Deck,
    Match,
    Round,
)
from apps.roulette.services import (
    active_round_for,
    both_owners_opted_in,
    end_round,
    opt_in,
    opted_in_user_ids,
    purge_expired_answers,
    release_match,
    start_round,
    submit_answer,
)


def _membership_or_denied(request, module: str) -> Membership:
    membership = (
        Membership.objects.filter(
            user=request.user,
            revoked_at__isnull=True,
            clubroom__deleted_at__isnull=True,
        )
        .select_related("clubroom")
        .first()
    )
    if membership is None or not membership.has_module_access(module):
        raise PermissionDenied("Kein Zugriff auf dieses Modul.")
    return membership


def _round_for_membership(pk: int, membership: Membership) -> Round:
    return get_object_or_404(
        Round.objects.select_related("deck", "started_by", "clubroom"),
        pk=pk,
        clubroom=membership.clubroom,
    )


def index(request):
    membership = _membership_or_denied(request, "roulette")
    clubroom = membership.clubroom
    purge_expired_answers()
    active_round = active_round_for(clubroom)
    decks = []
    for deck in Deck.objects.all():
        opted = both_owners_opted_in(clubroom, deck)
        decks.append(
            {
                "deck": deck,
                "opted": opted,
                "own_opted": request.user.id in opted_in_user_ids(clubroom, deck),
                "can_start": not deck.requires_opt_in or opted,
            }
        )
    return render(
        request,
        "roulette/index.html",
        {
            "clubroom": clubroom,
            "active_round": active_round,
            "decks": decks,
            "is_owner": membership.role == OWNER,
        },
    )


@login_required
@require_POST
def start(request, deck_id):
    membership = _membership_or_denied(request, "roulette")
    deck = get_object_or_404(Deck, pk=deck_id)
    try:
        round_obj = start_round(clubroom=membership.clubroom, deck=deck, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
        return redirect("roulette:index")
    return redirect("roulette:round", pk=round_obj.pk)


@login_required
@require_POST
def opt_in_deck(request, deck_id):
    membership = _membership_or_denied(request, "roulette")
    deck = get_object_or_404(Deck, pk=deck_id)
    try:
        opt_in(clubroom=membership.clubroom, deck=deck, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, f"Opt-in für Deck {deck.code} gespeichert.")
    return redirect("roulette:index")


def round_detail(request, pk):
    membership = _membership_or_denied(request, "roulette")
    round_obj = _round_for_membership(pk, membership)
    questions = list(round_obj.deck.questions.all())
    own_answers = {
        answer.question_id: answer for answer in round_obj.answers.filter(user=request.user)
    }
    matches = {
        match.question_id: match
        for match in round_obj.matches.select_related("user_a", "user_b", "question")
    }
    revealed_question_ids = [
        question_id
        for question_id, match in matches.items()
        if match.is_released and match.result != RESULT_NONE
    ]
    answers_by_question: dict[int, dict[int, object]] = {}
    for answer in round_obj.answers.filter(question_id__in=revealed_question_ids).select_related(
        "user"
    ):
        answers_by_question.setdefault(answer.question_id, {})[answer.user_id] = answer

    states = []
    for question in questions:
        own = own_answers.get(question.id)
        match = matches.get(question.id)
        state = {
            "question": question,
            "own": own,
            "own_label": ANSWER_LABELS.get(own.answer) if own else None,
            "match": match,
            "own_released": bool(match and match.released_by(request.user)),
            "is_released": bool(match and match.is_released),
            "result_label": None,
            "boundary_respected": False,
            "partner_label": None,
            "partner_name": None,
            "answers_deleted": False,
            "waiting_for_partner": bool(own and not match),
            "can_release": bool(
                match
                and round_obj.is_active
                and not match.is_released
                and not match.released_by(request.user)
            ),
        }
        if match is not None:
            partner = match.user_b if match.user_a_id == request.user.id else match.user_a
            state["partner_name"] = partner.username
            if match.is_released:
                state["result_label"] = (
                    "Kein Match" if match.result == RESULT_NONE else match.get_result_display()
                )
                state["boundary_respected"] = match.has_boundary
                if match.result != RESULT_NONE:
                    other_id = (
                        match.user_b_id if match.user_a_id == request.user.id else match.user_a_id
                    )
                    other_answer = answers_by_question.get(question.id, {}).get(other_id)
                    own_answer = answers_by_question.get(question.id, {}).get(request.user.id)
                    state["answers_deleted"] = bool(
                        (own_answer and own_answer.is_deleted)
                        or (other_answer and other_answer.is_deleted)
                    )
                    if other_answer and not other_answer.is_deleted:
                        state["partner_label"] = ANSWER_LABELS.get(other_answer.answer)
                    if own_answer and not own_answer.is_deleted:
                        state["own_label"] = ANSWER_LABELS.get(own_answer.answer)
        states.append(state)

    return render(
        request,
        "roulette/round.html",
        {
            "clubroom": membership.clubroom,
            "round": round_obj,
            "states": states,
            "form": AnswerForm(),
        },
    )


@login_required
@require_POST
def answer(request, round_pk, question_id):
    membership = _membership_or_denied(request, "roulette")
    round_obj = _round_for_membership(round_pk, membership)
    question = get_object_or_404(round_obj.deck.questions.all(), pk=question_id)
    form = AnswerForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Bitte eine gültige Antwort wählen.")
        return redirect("roulette:round", pk=round_obj.pk)
    try:
        submit_answer(
            round_obj=round_obj,
            question=question,
            user=request.user,
            answer=form.cleaned_data["answer"],
            is_boundary=form.cleaned_data["is_boundary"],
        )
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Antwort gespeichert.")
    return redirect("roulette:round", pk=round_obj.pk)


@login_required
@require_POST
def release(request, pk):
    membership = _membership_or_denied(request, "roulette")
    match = get_object_or_404(Match, pk=pk, round__clubroom=membership.clubroom)
    try:
        released = release_match(match=match, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        if released.is_released:
            messages.success(request, "Beide haben freigegeben.")
        else:
            messages.success(request, "Freigabe gespeichert. Warte auf dein Gegenüber.")
    return redirect("roulette:round", pk=match.round_id)


@login_required
@require_POST
def close_round(request, pk):
    membership = _membership_or_denied(request, "roulette")
    round_obj = _round_for_membership(pk, membership)
    try:
        end_round(round_obj=round_obj, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Runde beendet. Antworten wurden gelöscht, Matches bleiben.")
    return redirect("roulette:index")
