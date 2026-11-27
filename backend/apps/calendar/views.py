import calendar as pycalendar
from datetime import date, datetime, time, timedelta

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
    view = request.GET.get("ansicht", "monat")
    if view not in {"tag", "woche", "monat", "agenda"}:
        view = "monat"
    try:
        selected_date = date.fromisoformat(request.GET.get("datum", ""))
    except ValueError:
        selected_date = today
    try:
        year = int(request.GET.get("jahr", selected_date.year))
        month = int(request.GET.get("monat", selected_date.month))
        if not 1 <= month <= 12:
            raise ValueError
    except ValueError:
        year, month = selected_date.year, selected_date.month

    if view == "tag":
        start = datetime.combine(selected_date, time.min, tzinfo=timezone.get_current_timezone())
        end = start + timedelta(days=1)
        entries = CalendarEntry.objects.filter(
            clubroom=clubroom, start_at__gte=start, start_at__lt=end
        )
        month = selected_date.month
        year = selected_date.year
    elif view == "woche":
        start_date = selected_date - timedelta(days=selected_date.weekday())
        end_date = start_date + timedelta(days=7)
        start = datetime.combine(start_date, time.min, tzinfo=timezone.get_current_timezone())
        end = datetime.combine(end_date, time.min, tzinfo=timezone.get_current_timezone())
        entries = CalendarEntry.objects.filter(
            clubroom=clubroom, start_at__gte=start, start_at__lt=end
        )
        month = selected_date.month
        year = selected_date.year
    elif view == "agenda":
        entries = CalendarEntry.objects.filter(
            clubroom=clubroom, start_at__gte=timezone.now()
        ).order_by("start_at")[:100]
    else:
        first = datetime(year, month, 1, tzinfo=timezone.get_current_timezone())
        last_day = pycalendar.monthrange(year, month)[1]
        last = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.get_current_timezone())
        entries = CalendarEntry.objects.filter(
            clubroom=clubroom, start_at__gte=first, start_at__lte=last
        )
    entries = entries.select_related("created_by")

    initial = {}
    if request.GET.get("datum"):
        initial["start_at"] = datetime.combine(
            selected_date, time(19, 0), tzinfo=timezone.get_current_timezone()
        )
    form = (
        CalendarEntryForm(initial=initial)
        if view in {"tag", "woche", "monat"}
        else CalendarEntryForm()
    )
    if request.method == "POST":
        form = CalendarEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.clubroom = clubroom
            entry.created_by = request.user
            entry.save()
            messages.success(request, "Kalendereintrag gespeichert.")
            return redirect("calendar:index")

    entries_list = list(entries)
    entries_by_day = {}
    for entry in entries_list:
        entries_by_day.setdefault(timezone.localtime(entry.start_at).date(), []).append(entry)
    calendar_weeks = []
    if view == "monat":
        for week in pycalendar.Calendar(firstweekday=0).monthdayscalendar(year, month):
            week_days = []
            for day_number in week:
                if day_number == 0:
                    week_days.append(
                        {"day": "", "in_month": False, "today": False, "entries": [], "date": None}
                    )
                    continue
                current = date(year, month, day_number)
                week_days.append(
                    {
                        "day": day_number,
                        "in_month": True,
                        "today": current == today,
                        "entries": entries_by_day.get(current, []),
                        "date": current,
                    }
                )
            calendar_weeks.append(week_days)
    week_start = selected_date - timedelta(days=selected_date.weekday())
    week_days = []
    for index in range(7):
        current = week_start + timedelta(days=index)
        week_days.append(
            {"date": current, "today": current == today, "entries": entries_by_day.get(current, [])}
        )
    if view == "tag":
        prev_date, next_date = selected_date - timedelta(days=1), selected_date + timedelta(days=1)
    elif view == "woche":
        prev_date, next_date = week_start - timedelta(days=7), week_start + timedelta(days=7)
    else:
        prev_date, next_date = selected_date, selected_date
    if view == "monat":
        prev_date = date(year - 1 if month == 1 else year, 12 if month == 1 else month - 1, 1)
        next_date = date(year + 1 if month == 12 else year, 1 if month == 12 else month + 1, 1)
    token = CalendarFeedToken.objects.filter(clubroom=clubroom, user=request.user).first()
    return render(
        request,
        "calendar/index.html",
        {
            "clubroom": clubroom,
            "membership": membership,
            "entries": entries_list,
            "form": form,
            "year": year,
            "month": month,
            "month_label": pycalendar.month_name[month],
            "view": view,
            "selected_date": selected_date,
            "week_days": week_days,
            "calendar_weeks": calendar_weeks,
            "prev_date": prev_date,
            "next_date": next_date,
            "feed_token": token,
            "feed_raw": request.session.pop("calendar_feed_raw", ""),
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
