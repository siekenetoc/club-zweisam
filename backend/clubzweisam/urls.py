from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from apps.core.views import HealthView

urlpatterns = [
    path("", include("apps.clubroom.urls")),
    path("", include("apps.accounts.urls")),
    path("healthz", HealthView.as_view(), name="healthz"),
    path("admin/", admin.site.urls),
    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
