from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.admin_panel.forms import BreakGlassRequestForm
from apps.admin_panel.models import BreakGlassRequest
from apps.admin_panel.services import (
    approve_break_glass,
    request_break_glass,
    use_break_glass,
)
from apps.clubroom.models import Clubroom, Membership
from apps.playbook.models import Challenge
from apps.roulette.models import Match
from apps.wishes.models import Wish


def _superuser_or_denied(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Nur Super-Admins.")


@staff_member_required
def dashboard(request):
    pending = BreakGlassRequest.objects.filter(approved_at__isnull=True).count()
    return render(
        request,
        "admin_panel/dashboard.html",
        {
            "user_count": User.objects.count(),
            "clubroom_count": Clubroom.objects.filter(deleted_at__isnull=True).count(),
            "active_memberships": Membership.objects.filter(revoked_at__isnull=True).count(),
            "wish_count": Wish.objects.filter(deleted_at__isnull=True).count(),
            "match_count": Match.objects.count(),
            "challenge_count": Challenge.objects.count(),
            "pending_break_glass": pending,
            "is_superuser": request.user.is_superuser,
        },
    )


@staff_member_required
def break_glass(request):
    _superuser_or_denied(request)
    if request.method == "POST":
        form = BreakGlassRequestForm(request.POST)
        if form.is_valid():
            try:
                request_break_glass(
                    user=request.user,
                    target_type=form.cleaned_data["target_type"],
                    target_id=form.cleaned_data["target_id"],
                    reason=form.cleaned_data["reason"],
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    "Antrag gestellt. Eine zweite Super-Admin-Person muss bestätigen.",
                )
                return redirect("admin_panel:break_glass")
    else:
        form = BreakGlassRequestForm()

    requests = BreakGlassRequest.objects.select_related("requested_by", "approved_by")[:50]
    return render(
        request,
        "admin_panel/breakglass.html",
        {"form": form, "requests": requests},
    )


@staff_member_required
@require_POST
def break_glass_approve(request, pk):
    _superuser_or_denied(request)
    break_glass_request = get_object_or_404(BreakGlassRequest, pk=pk)
    try:
        approve_break_glass(request_obj=break_glass_request, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Antrag bestätigt. Gültig für 24 Stunden.")
    return redirect("admin_panel:break_glass")


@staff_member_required
@require_POST
def break_glass_use(request, pk):
    _superuser_or_denied(request)
    break_glass_request = get_object_or_404(BreakGlassRequest, pk=pk)
    try:
        use_break_glass(request_obj=break_glass_request, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(
            request,
            "Zugriff protokolliert und betroffene Nutzer benachrichtigt.",
        )
    return redirect("admin_panel:break_glass")
