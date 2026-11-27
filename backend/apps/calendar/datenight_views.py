from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.calendar.datenight_forms import DateNightForm
from apps.calendar.models import (
    STATUS_ACCEPTED,
    STATUS_CANCELLED,
    STATUS_DECLINED,
    STATUS_PROPOSED,
    CalendarEntry,
    DateNight,
)
from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER


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
        or not membership.has_module_access("calendar")
    ):
        raise PermissionDenied("Kein Zugriff auf DateNight.")
    return membership


def index(request):
    membership = _owner(request)
    clubroom = membership.clubroom
    open_night = (
        DateNight.objects.filter(clubroom=clubroom, status=STATUS_PROPOSED)
        .select_related("proposed_by")
        .first()
    )
    accepted = DateNight.objects.filter(
        clubroom=clubroom, status=STATUS_ACCEPTED, scheduled_for__gte=timezone.now()
    ).select_related("proposed_by")[:5]
    history = DateNight.objects.filter(clubroom=clubroom).exclude(status=STATUS_PROPOSED)[:10]
    form = DateNightForm()
    if request.method == "POST":
        form = DateNightForm(request.POST)
        if form.is_valid():
            night = form.save(commit=False)
            night.clubroom = clubroom
            night.proposed_by = request.user
            night.save()
            messages.success(request, "DateNight vorgeschlagen.")
            return redirect("datenight:index")
    return render(
        request,
        "datenight/index.html",
        {
            "clubroom": clubroom,
            "form": form,
            "open_night": open_night,
            "accepted": accepted,
            "history": history,
        },
    )


@login_required
@require_POST
def respond(request, pk):
    membership = _owner(request)
    night = get_object_or_404(DateNight, pk=pk, clubroom=membership.clubroom)
    action = request.POST.get("action")
    if night.status != STATUS_PROPOSED:
        messages.error(request, "Diese DateNight ist nicht mehr offen.")
        return redirect("datenight:index")
    if night.proposed_by_id == request.user.id:
        messages.error(request, "Die Antwort muss von der anderen Person kommen.")
        return redirect("datenight:index")
    if action == "accept":
        night.status = STATUS_ACCEPTED
        night.responded_by = request.user
        night.responded_at = timezone.now()
        night.save(update_fields=["status", "responded_by", "responded_at", "updated_at"])
        CalendarEntry.objects.create(
            clubroom=membership.clubroom,
            created_by=request.user,
            kind="event",
            title=f"DateNight: {night.motto}",
            description=night.note,
            start_at=night.scheduled_for,
            end_at=night.scheduled_for + timedelta(hours=2),
        )
        messages.success(request, "DateNight bestätigt und im Kalender eingetragen.")
    elif action == "decline":
        night.status = STATUS_DECLINED
        night.responded_by = request.user
        night.responded_at = timezone.now()
        night.save(update_fields=["status", "responded_by", "responded_at", "updated_at"])
        messages.success(request, "DateNight abgelehnt.")
    return redirect("datenight:index")


@login_required
@require_POST
def cancel(request, pk):
    membership = _owner(request)
    night = get_object_or_404(DateNight, pk=pk, clubroom=membership.clubroom)
    if night.status not in {STATUS_PROPOSED, STATUS_ACCEPTED}:
        messages.error(request, "Diese DateNight kann nicht abgesagt werden.")
    else:
        night.status = STATUS_CANCELLED
        night.responded_by = request.user
        night.responded_at = timezone.now()
        night.save(update_fields=["status", "responded_by", "responded_at", "updated_at"])
        messages.success(request, "DateNight abgesagt.")
    return redirect("datenight:index")
