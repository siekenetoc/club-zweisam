from django.contrib import messages
from django.shortcuts import redirect

from apps.core.permissions import is_platform_admin

APP_PATH_PREFIXES = (
    "/clubraum/",
    "/einladung/",
    "/separee/",
    "/vitrine/",
    "/concierge/",
    "/playbook/",
    "/lounge/",
    "/logbuch/",
    "/deep-talk/",
    "/krisenmodus/",
    "/punkte/",
    "/kalender/",
    "/stimmung/",
    "/nachrichten/",
    "/galerie/",
    "/erkenntnisse/",
)


class AdminAppAccessMiddleware:
    """Admin-Konten verwalten das Portal, nutzen aber nicht die Dyaden-App."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.is_staff:
            path = request.path_info
            if path == "/" or path.startswith(APP_PATH_PREFIXES):
                messages.warning(
                    request,
                    "Admin-Konto: App-Funktionen sind deaktiviert. "
                    "Für Tests bitte einen separaten Nicht-Staff-Account verwenden.",
                )
                if is_platform_admin(user):
                    return redirect("/management/")
                return redirect("/admin/")
        return self.get_response(request)
