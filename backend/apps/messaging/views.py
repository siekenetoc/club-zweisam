from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER
from apps.feed.models import EVENT_MESSAGE_CREATED
from apps.feed.services import record_event
from apps.messaging.forms import MessageForm
from apps.messaging.models import KIND_QUICK, KIND_TEXT, QUICK_MESSAGES, Message


def _membership_or_denied(request):
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
        or not membership.has_module_access("messages")
    ):
        raise PermissionDenied("Kein Zugriff auf Nachrichten.")
    return membership


def index(request):
    membership = _membership_or_denied(request)
    clubroom = membership.clubroom
    messages_list = Message.objects.filter(
        clubroom=clubroom, deleted_at__isnull=True
    ).select_related("sender")[:200]
    Message.objects.filter(clubroom=clubroom, deleted_at__isnull=True).exclude(
        sender=request.user
    ).filter(read_at__isnull=True).update(read_at=timezone.now())
    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            Message.objects.create(
                clubroom=clubroom,
                sender=request.user,
                body=form.cleaned_data["body"],
                kind=KIND_TEXT,
            )
            record_event(
                clubroom=clubroom,
                event_type=EVENT_MESSAGE_CREATED,
                actor=request.user,
                target_type="messaging.message",
                target_id="thread",
            )
            messages.success(request, "Nachricht gesendet.")
            return redirect("messaging:index")
    else:
        form = MessageForm()
    return render(
        request,
        "messaging/index.html",
        {
            "clubroom": clubroom,
            "membership": membership,
            "messages_list": messages_list,
            "form": form,
            "quick_messages": QUICK_MESSAGES,
        },
    )


@login_required
@require_POST
def send_quick(request):
    membership = _membership_or_denied(request)
    key = request.POST.get("quick_key", "")
    if key not in dict(QUICK_MESSAGES):
        messages.error(request, "Unbekanntes Kurzsignal.")
        return redirect("messaging:index")
    Message.objects.create(
        clubroom=membership.clubroom,
        sender=request.user,
        kind=KIND_QUICK,
        quick_key=key,
    )
    record_event(
        clubroom=membership.clubroom,
        event_type=EVENT_MESSAGE_CREATED,
        actor=request.user,
        target_type="messaging.message",
        target_id="thread",
    )
    return redirect("messaging:index")


@login_required
@require_POST
def delete_message(request, pk):
    membership = _membership_or_denied(request)
    message = get_object_or_404(Message, pk=pk, clubroom=membership.clubroom, sender=request.user)
    message.deleted_at = timezone.now()
    message.body = ""
    message.save(update_fields=["deleted_at", "body", "updated_at"])
    return redirect("messaging:index")
