from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

if SECRET_KEY == "dev-insecure-secret-key-change-me":  # noqa: F405
    raise ImproperlyConfigured("SECRET_KEY muss in Produktion gesetzt werden.")

if not DATABASE_URL:  # noqa: F405
    raise ImproperlyConfigured("DATABASE_URL muss in Produktion gesetzt werden.")

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
