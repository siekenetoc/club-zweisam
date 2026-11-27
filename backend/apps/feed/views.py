from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER
from apps.feed.models import EVENT_CHOICES, FeedEvent


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
    if membership is None or not membership.has_module_access("feed"):
        raise PermissionDenied("Kein Zugriff auf das Logbuch.")
    return membership


def index(request):
    membership = _membership_or_denied(request)
    events = FeedEvent.objects.filter(clubroom=membership.clubroom).select_related("actor")
    event_filter = request.GET.get("typ", "")
    valid_types = {value for value, _ in EVENT_CHOICES}
    if event_filter in valid_types:
        events = events.filter(event_type=event_filter)
    else:
        event_filter = ""

    sort = request.GET.get("sort", "created_at")
    direction = request.GET.get("dir", "desc")
    sort_fields = {
        "created_at": "created_at",
        "event_type": "event_type",
        "actor": "actor__username",
    }
    if sort not in sort_fields:
        sort = "created_at"
    if direction not in {"asc", "desc"}:
        direction = "desc"
    prefix = "" if direction == "asc" else "-"
    events = events.order_by(f"{prefix}{sort_fields[sort]}", "-id")
    return render(
        request,
        "feed/index.html",
        {
            "clubroom": membership.clubroom,
            "events": events[:100],
            "event_types": EVENT_CHOICES,
            "event_filter": event_filter,
            "is_owner": membership.role == OWNER,
            "sort": sort,
            "direction": direction,
        },
    )


@login_required
@require_POST
def remove(request, pk):
    membership = _membership_or_denied(request)
    event = get_object_or_404(FeedEvent, pk=pk, clubroom=membership.clubroom)
    if event.actor_id != request.user.id and membership.role != OWNER:
        raise PermissionDenied("Kein Recht, diesen Eintrag zu entfernen.")
    event.soft_delete()
    messages.success(request, "Eintrag entfernt.")
    return redirect("feed:index")
