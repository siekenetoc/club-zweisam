from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER
from apps.gallery.models import GalleryImage
from apps.insights.models import Insight
from apps.moments.forms import DailyAnswerForm
from apps.moments.models import DailyAnswer, question_for


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
        or not membership.has_module_access("moments")
    ):
        raise PermissionDenied("Kein Zugriff auf Momente.")
    return membership


def index(request):
    membership = _owner(request)
    clubroom = membership.clubroom
    day = timezone.localdate()
    question = question_for(day)
    answers = list(DailyAnswer.objects.filter(clubroom=clubroom, date=day).select_related("user"))
    own = next((answer for answer in answers if answer.user_id == request.user.id), None)
    partner = next((answer for answer in answers if answer.user_id != request.user.id), None)
    reveal = own is not None and partner is not None
    memories = GalleryImage.objects.filter(
        album__clubroom=clubroom,
        created_at__month=day.month,
        created_at__day=day.day,
        created_at__year__lt=day.year,
    ).select_related("album")[:6]
    insights = Insight.objects.filter(
        clubroom=clubroom,
        status="shared",
        created_at__month=day.month,
        created_at__day=day.day,
        created_at__year__lt=day.year,
    )[:4]
    return render(
        request,
        "moments/index.html",
        {
            "clubroom": clubroom,
            "day": day,
            "question": question,
            "own_answer": own,
            "partner_answer": partner if reveal else None,
            "reveal": reveal,
            "form": DailyAnswerForm(),
            "memories": memories,
            "insights": insights,
        },
    )


@login_required
@require_POST
def answer(request):
    membership = _owner(request)
    form = DailyAnswerForm(request.POST)
    if form.is_valid():
        DailyAnswer.objects.update_or_create(
            clubroom=membership.clubroom,
            user=request.user,
            date=timezone.localdate(),
            defaults={"answer": form.cleaned_data["answer"]},
        )
        messages.success(
            request, "Antwort gespeichert. Sie bleibt verborgen, bis beide geantwortet haben."
        )
    return redirect("moments:index")
