from datetime import timedelta

from django.db.models import Avg
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import ClubroomMember
from apps.api.serializers import (
    AlbumSerializer,
    CalendarEntrySerializer,
    InsightSerializer,
    MessageSerializer,
    ProfileSerializer,
)
from apps.calendar.models import CalendarEntry
from apps.gallery.models import Album
from apps.insights.models import Insight
from apps.lounge.models import CheckIn
from apps.messaging.models import Message


class MemberView(APIView):
    permission_classes = [ClubroomMember]

    def membership(self, request):
        return ClubroomMember().membership(request)


class ProfileView(MemberView):
    def get(self, request):
        return Response(ProfileSerializer(request.user).data)


class MoodView(MemberView):
    def get(self, request):
        days = 30
        try:
            days = int(request.query_params.get("tage", "30"))
        except ValueError:
            pass
        if days not in {7, 30, 90}:
            days = 30
        start = timezone.localdate() - timedelta(days=days - 1)
        rows = (
            CheckIn.objects.filter(clubroom=self.membership(request).clubroom, date__gte=start)
            .values("date", "user__username", "user__display_name")
            .annotate(mood=Avg("mood"), energy=Avg("energy"), closeness=Avg("closeness"))
            .order_by("date", "user__username")
        )
        return Response({"days": days, "series": list(rows)})


class MessageListView(MemberView):
    def get(self, request):
        messages = Message.objects.filter(
            clubroom=self.membership(request).clubroom, deleted_at__isnull=True
        ).select_related("sender")[:100]
        return Response(MessageSerializer(messages, many=True).data)


class CalendarListView(MemberView):
    def get(self, request):
        entries = CalendarEntry.objects.filter(clubroom=self.membership(request).clubroom)[:200]
        return Response(CalendarEntrySerializer(entries, many=True).data)


class AlbumListView(MemberView):
    def get(self, request):
        albums = Album.objects.filter(clubroom=self.membership(request).clubroom).prefetch_related(
            "images"
        )
        return Response(AlbumSerializer(albums, many=True).data)


class InsightListView(MemberView):
    def get(self, request):
        insights = Insight.objects.filter(
            clubroom=self.membership(request).clubroom,
            status="shared",
        ).select_related("author")[:100]
        return Response(InsightSerializer(insights, many=True).data)
