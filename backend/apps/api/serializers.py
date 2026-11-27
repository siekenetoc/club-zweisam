from rest_framework import serializers

from apps.accounts.models import User
from apps.calendar.models import CalendarEntry
from apps.gallery.models import Album
from apps.insights.models import Insight
from apps.messaging.models import Message


class ProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    thumb_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "username",
            "display_name",
            "first_name",
            "last_name",
            "pronouns",
            "bio",
            "timezone",
            "avatar_url",
            "thumb_url",
        )

    def get_avatar_url(self, obj):
        return obj.avatar.url if obj.avatar else ""

    def get_thumb_url(self, obj):
        return obj.avatar_thumb.url if obj.avatar_thumb else ""


class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.CharField(source="sender.display_label", read_only=True)

    class Meta:
        model = Message
        fields = ("id", "sender", "kind", "quick_key", "body", "created_at", "read_at")


class CalendarEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEntry
        fields = ("id", "kind", "title", "description", "start_at", "end_at", "all_day", "is_done")


class AlbumSerializer(serializers.ModelSerializer):
    image_count = serializers.IntegerField(source="images.count", read_only=True)

    class Meta:
        model = Album
        fields = ("id", "title", "description", "image_count", "created_at")


class InsightSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.display_label", read_only=True)

    class Meta:
        model = Insight
        fields = ("id", "author", "title", "body", "status", "created_at")
