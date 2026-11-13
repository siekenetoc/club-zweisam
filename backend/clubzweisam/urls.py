from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve

from apps.core.views import HealthView, HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("healthz", HealthView.as_view(), name="healthz"),
    path("admin/", admin.site.urls),
    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
