from urllib.parse import urlparse

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class ClubAccountAdapter(DefaultAccountAdapter):
    def _public_url(self, url: str) -> str:
        if not url:
            return url
        base = settings.PORTAL_BASE_URL.rstrip("/")
        parsed = urlparse(url)
        result = f"{base}{parsed.path}"
        if parsed.query:
            result += f"?{parsed.query}"
        if parsed.fragment:
            result += f"#{parsed.fragment}"
        return result

    def get_email_confirmation_url(self, request, emailconfirmation):
        return self._public_url(super().get_email_confirmation_url(request, emailconfirmation))

    def get_reset_password_from_key_url(self, key: str) -> str:
        return self._public_url(super().get_reset_password_from_key_url(key))
