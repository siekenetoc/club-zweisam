from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from apps.clubroom.models import Membership
from apps.roulette.models import Match
from apps.vitrine.models import SOURCE_MATCH, Commonality


def _membership_or_denied(request) -> Membership:
    membership = (
        Membership.objects.filter(
            user=request.user,
            revoked_at__isnull=True,
            clubroom__deleted_at__isnull=True,
        )
        .select_related("clubroom")
        .first()
    )
    if membership is None or not membership.has_module_access("vitrine"):
        raise PermissionDenied("Kein Zugriff auf die Vitrine.")
    return membership


@login_required
def index(request):
    membership = _membership_or_denied(request)
    commonalities = list(
        Commonality.objects.filter(clubroom=membership.clubroom, source_type=SOURCE_MATCH)
    )
    matches = {
        match.pk: match
        for match in Match.objects.filter(
            pk__in=[item.source_id for item in commonalities]
        ).select_related("question", "question__deck", "round")
    }
    entries = []
    for commonality in commonalities:
        match = matches.get(commonality.source_id)
        if match is None:
            continue
        entries.append(
            {
                "category": commonality.category,
                "question": match.question.text,
                "deck": match.question.deck.title,
                "result": match.get_result_display(),
                "created_at": commonality.created_at,
            }
        )
    return render(
        request,
        "vitrine/index.html",
        {"clubroom": membership.clubroom, "entries": entries},
    )
