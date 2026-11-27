from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER
from apps.insights.forms import InsightForm
from apps.insights.models import Insight, InsightVote


def _owner(request):
    membership = (
        Membership.objects.filter(
            user=request.user,
            revoked_at__isnull=True,
            clubroom__deleted_at__isnull=True,
        )
        .select_related("clubroom")
        .first()
    )
    if (
        membership is None
        or membership.role != OWNER
        or not membership.has_module_access("insights")
    ):
        raise PermissionDenied("Kein Zugriff auf Erkenntnisse.")
    return membership


@login_required
def index(request):
    membership = _owner(request)
    clubroom = membership.clubroom
    insights = (
        Insight.objects.filter(clubroom=clubroom)
        .filter(Q(status="shared") | Q(author=request.user))
        .select_related("author")
        .prefetch_related("votes")[:100]
    )
    form = InsightForm()
    if request.method == "POST":
        form = InsightForm(request.POST)
        if form.is_valid():
            insight = form.save(commit=False)
            insight.clubroom = clubroom
            insight.author = request.user
            insight.status = "shared" if request.POST.get("share") == "on" else "private"
            insight.save()
            messages.success(request, "Erkenntnis gespeichert.")
            return redirect("insights:index")
    votes = {
        vote.insight_id: vote
        for vote in InsightVote.objects.filter(user=request.user, insight__in=insights)
    }
    return render(
        request,
        "insights/index.html",
        {"clubroom": clubroom, "insights": insights, "form": form, "votes": votes},
    )


@login_required
@require_POST
def share(request, pk):
    membership = _owner(request)
    insight = get_object_or_404(Insight, pk=pk, clubroom=membership.clubroom, author=request.user)
    insight.status = "shared"
    insight.save(update_fields=["status", "updated_at"])
    return redirect("insights:index")


@login_required
@require_POST
def vote(request, pk):
    membership = _owner(request)
    insight = get_object_or_404(Insight, pk=pk, clubroom=membership.clubroom, status="shared")
    value = request.POST.get("value")
    if value not in {"agree", "unsure", "disagree"}:
        messages.error(request, "Ungültige Abstimmung.")
    else:
        InsightVote.objects.update_or_create(
            insight=insight, user=request.user, defaults={"value": value}
        )
    return redirect("insights:index")


@login_required
@require_POST
def delete(request, pk):
    membership = _owner(request)
    insight = get_object_or_404(Insight, pk=pk, clubroom=membership.clubroom, author=request.user)
    insight.delete()
    return redirect("insights:index")
