from django.urls import path

from apps.api import views

app_name = "api"

urlpatterns = [
    path("me/", views.ProfileView.as_view(), name="me"),
    path("mood/", views.MoodView.as_view(), name="mood"),
    path("messages/", views.MessageListView.as_view(), name="messages"),
    path("calendar/", views.CalendarListView.as_view(), name="calendar"),
    path("albums/", views.AlbumListView.as_view(), name="albums"),
    path("insights/", views.InsightListView.as_view(), name="insights"),
]
