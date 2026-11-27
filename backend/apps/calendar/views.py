import calendar as pycalendar
from datetime import date, datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.calendar.forms import CalendarEntryForm
from apps.calendar.ics import build_ics
from apps.calendar.models import CalendarEntry, CalendarFeedToken
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
    if membership is None or not membership.has_module_access("calendar"):
        raise PermissionDenied("Kein Zugriff auf den Kalender.")
    if membership.role != OWNER:
        raise PermissionDenied("Nur Hauptmitglieder verwalten den Kalender.")
    return membership


def index(request):
    membership = _owner(request)
    clubroom = membership.clubroom
    today = timezone.localdate()
    try:
        year = int(request.GET.get("jahr", today.year))
        month = int(request.GET.get("monat", today.month))
        if not 1 <= month <= 12:
            raise ValueError
    except ValueError:
        year, month = today.year, today.month
    first = datetime(year, month, 1, tzinfo=timezone.get_current_timezone())
    last_day = pycalendar.monthrange(year, month)[1]
    last = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.get_current_timezone())
    entries = CalendarEntry.objects.filter(
        clubroom=clubroom, start_at__gte=first, start_at__lte=last
    ).select_related("created_by")
    form = CalendarEntryForm()
    if request.method == "POST":
        form = CalendarEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.clubroom = clubroom
            entry.created_by = request.user
            entry.save()
            messages.success(request, "Kalendereintrag gespeichert.")
            return redirect("calendar:index")
    entries_by_day = {}
    for entry in entries:
        local_date = timezone.localtime(entry.start_at).date()
        entries_by_day.setdefault(local_date, []).append(entry)
    today_date = timezone.localdate()
    calendar_weeks = []
    for week in pycalendar.Calendar(firstweekday=0).monthdayscalendar(year, month):
        week_days = []
        for day_number in week:
            if day_number == 0:
                week_days.append({"day": "", "in_month": False, "today": False, "entries": []})
                continue
            current = date(year, month, day_number)
            week_days.append(
                {
                    "day": day_number,
                    "in_month": True,
                    "today": current == today_date,
                    "entries": entries_by_day.get(current, []),
                }
            )
        calendar_weeks.append(week_days)
    token = CalendarFeedToken.objects.filter(clubroom=clubroom, user=request.user).first()
    return render(
        request,
        "calendar/index.html",
        {
            "clubroom": clubroom,
            "membership": membership,
            "entries": entries,
            "form": form,
            "year": year,
            "month": month,
            "month_label": pycalendar.month_name[month],
            "prev_month": month - 1 or 12,
            "prev_year": year - 1 if month == 1 else year,
            "next_month": month % 12 + 1,
            "next_year": year + 1 if month == 12 else year,
            "feed_token": token,
            "feed_raw": request.session.pop("calendar_feed_raw", ""),
            "calendar_weeks": calendar_weeks,
        },
    )


@login_required
@require_POST
def delete_entry(request, pk):
    membership = _owner(request)
    entry = get_object_or_404(CalendarEntry, pk=pk, clubroom=membership.clubroom)
    entry.delete()
    messages.success(request, "Kalendereintrag gelöscht.")
    return redirect("calendar:index")


@login_required
@require_POST
def toggle_task(request, pk):
    membership = _owner(request)
    entry = get_object_or_404(CalendarEntry, pk=pk, clubroom=membership.clubroom)
    if entry.kind == "task":
        entry.is_done = not entry.is_done
        entry.done_at = timezone.now() if entry.is_done else None
        entry.save(update_fields=["is_done", "done_at", "updated_at"])
    return redirect("calendar:index")


@login_required
@require_POST
def regenerate_feed(request):
    membership = _owner(request)
    include_details = request.POST.get("include_details") == "on"
    token, raw = CalendarFeedToken.issue(
        clubroom=membership.clubroom,
        user=request.user,
        include_details=include_details,
    )
    request.session["calendar_feed_raw"] = raw
    messages.success(request, "Neuer Kalender-Abo-Link erzeugt.")
    return redirect("calendar:index")


def feed(request, token):
    token_hash = CalendarFeedToken.hash(token)
    feed_token = (
        CalendarFeedToken.objects.select_related("clubroom")
        .filter(token_hash=token_hash, revoked_at__isnull=True)
        .first()
    )
    if feed_token is None:
        raise Http404
    entries = CalendarEntry.objects.filter(clubroom=feed_token.clubroom)
    content = build_ics(
        entries,
        include_details=feed_token.include_details,
        domain=settings.PORTAL_BASE_URL.split("://")[-1],
    )
    response = HttpResponse(content, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = 'inline; filename="club-zweisam.ics"'
    response["Cache-Control"] = "no-store"
    return response
