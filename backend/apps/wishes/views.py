from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.clubroom.models import Membership
from apps.wishes.forms import WishForm, WishResponseForm
from apps.wishes.models import (
    STATUS_AGREED,
    STATUS_BOUNDARY,
    STATUS_CONFIRMED,
    STATUS_DRAFT,
    STATUS_PENDING,
    STATUS_PLACED,
    STATUS_POSTPONED,
    STATUS_REJECTED,
    STATUS_REPLIED,
    Wish,
)
from apps.wishes.services import (
    confirm_fulfilled,
    create_wish,
    mark_fulfilled,
    requester_decide,
    respond_to_wish,
    share_wish,
)

OPEN_STATUSES = {STATUS_PLACED, STATUS_REPLIED, STATUS_AGREED, STATUS_PENDING}
CLOSED_STATUSES = {
    STATUS_CONFIRMED,
    STATUS_REJECTED,
    STATUS_BOUNDARY,
    STATUS_POSTPONED,
}


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
    if membership is None or not membership.has_module_access("wishes"):
        raise PermissionDenied("Kein Zugriff auf den Concierge.")
    return membership


def _visible_wishes(membership, user):
    return Wish.objects.filter(
        Q(is_private=False) | Q(created_by=user),
        clubroom=membership.clubroom,
        deleted_at__isnull=True,
    ).select_related("created_by")


def index(request):
    membership = _membership_or_denied(request)
    wishes = list(_visible_wishes(membership, request.user))
    incoming = [
        wish
        for wish in wishes
        if wish.status == STATUS_PLACED and wish.created_by_id != request.user.id
    ]
    outgoing = [wish for wish in wishes if wish.created_by_id == request.user.id]
    private = [wish for wish in outgoing if wish.status == STATUS_DRAFT]
    closed = [
        wish
        for wish in wishes
        if wish.status in CLOSED_STATUSES and wish.created_by_id != request.user.id
    ]
    return render(
        request,
        "wishes/index.html",
        {
            "clubroom": membership.clubroom,
            "incoming": incoming,
            "outgoing": outgoing,
            "private": private,
            "closed": closed,
        },
    )


@login_required
def create(request):
    membership = _membership_or_denied(request)
    if request.method == "POST":
        form = WishForm(request.POST)
        if form.is_valid():
            try:
                wish = create_wish(
                    clubroom=membership.clubroom,
                    user=request.user,
                    wish_type=form.cleaned_data["type"],
                    title=form.cleaned_data["title"],
                    body=form.cleaned_data["body"],
                    category=form.cleaned_data["category"],
                    intensity=int(form.cleaned_data["intensity"]),
                    timeframe=form.cleaned_data["timeframe"],
                    is_private=form.cleaned_data["is_private"],
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, "Wunsch gespeichert.")
                return redirect("wishes:detail", pk=wish.pk)
    else:
        form = WishForm()
    return render(request, "wishes/create.html", {"form": form, "clubroom": membership.clubroom})


def _visible_wish_or_404(pk, user, membership):
    wish = get_object_or_404(
        Wish.objects.select_related("clubroom", "created_by"),
        pk=pk,
        clubroom=membership.clubroom,
        deleted_at__isnull=True,
    )
    if wish.is_private and wish.created_by_id != user.id:
        raise PermissionDenied("Dieser Wunsch ist privat.")
    return wish


def detail(request, pk):
    membership = _membership_or_denied(request)
    wish = _visible_wish_or_404(pk, request.user, membership)
    responses = wish.responses.select_related("responded_by")
    latest_response = responses.order_by("-created_at").first()
    is_creator = wish.created_by_id == request.user.id
    can_respond = not is_creator and wish.status == STATUS_PLACED and not wish.is_private
    can_decide = (
        is_creator
        and wish.status == STATUS_REPLIED
        and latest_response is not None
        and latest_response.action in {"partial", "alternative"}
    )
    can_fulfill = is_creator and wish.status == STATUS_AGREED
    can_confirm = (
        not is_creator
        and wish.status == STATUS_PENDING
        and latest_response is not None
        and latest_response.responded_by_id == request.user.id
    )
    return render(
        request,
        "wishes/detail.html",
        {
            "clubroom": membership.clubroom,
            "wish": wish,
            "responses": responses,
            "latest_response": latest_response,
            "is_creator": is_creator,
            "can_respond": can_respond,
            "can_decide": can_decide,
            "can_fulfill": can_fulfill,
            "can_confirm": can_confirm,
            "response_form": WishResponseForm(),
        },
    )


@login_required
@require_POST
def respond(request, pk):
    membership = _membership_or_denied(request)
    wish = _visible_wish_or_404(pk, request.user, membership)
    form = WishResponseForm(request.POST)
    if not form.is_valid():
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
        return redirect("wishes:detail", pk=wish.pk)
    try:
        respond_to_wish(
            wish=wish,
            user=request.user,
            action=form.cleaned_data["action"],
            note=form.cleaned_data["note"],
        )
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Antwort gespeichert.")
    return redirect("wishes:detail", pk=wish.pk)


@login_required
@require_POST
def decide(request, pk):
    membership = _membership_or_denied(request)
    wish = _visible_wish_or_404(pk, request.user, membership)
    accept = request.POST.get("accept") == "1"
    try:
        requester_decide(wish=wish, user=request.user, accept=accept)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Entscheidung gespeichert.")
    return redirect("wishes:detail", pk=wish.pk)


@login_required
@require_POST
def fulfill(request, pk):
    membership = _membership_or_denied(request)
    wish = _visible_wish_or_404(pk, request.user, membership)
    try:
        mark_fulfilled(wish=wish, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Erfüllung gemeldet. Warte auf die Bestätigung.")
    return redirect("wishes:detail", pk=wish.pk)


@login_required
@require_POST
def confirm(request, pk):
    membership = _membership_or_denied(request)
    wish = _visible_wish_or_404(pk, request.user, membership)
    try:
        confirm_fulfilled(wish=wish, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Wunsch bestätigt.")
    return redirect("wishes:detail", pk=wish.pk)


@login_required
@require_POST
def share(request, pk):
    membership = _membership_or_denied(request)
    wish = _visible_wish_or_404(pk, request.user, membership)
    try:
        share_wish(wish=wish, user=request.user)
    except ValidationError as exc:
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.success(request, "Wunsch geteilt.")
    return redirect("wishes:detail", pk=wish.pk)
