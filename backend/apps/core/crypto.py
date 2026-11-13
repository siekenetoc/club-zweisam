from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

ENCRYPTED_PREFIX = "enc:v1:"


class EncryptionError(RuntimeError):
    pass


def generate_key() -> str:
    return Fernet.generate_key().decode("ascii")


@lru_cache(maxsize=8)
def _fernet_for(key: str) -> Fernet:
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEY ist kein gültiger Fernet-Schlüssel."
        ) from exc


def fernet() -> Fernet:
    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY ist nicht gesetzt.")
    return _fernet_for(key)


def is_encrypted(value: object) -> bool:
    return isinstance(value, str) and value.startswith(ENCRYPTED_PREFIX)


def encrypt_text(value: str) -> str:
    token = fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return f"{ENCRYPTED_PREFIX}{token}"


def decrypt_text(value: str) -> str:
    if not is_encrypted(value):
        return value
    token = value[len(ENCRYPTED_PREFIX) :].encode("ascii")
    try:
        return fernet().decrypt(token).decode("utf-8")
    except InvalidToken:
        old_key = getattr(settings, "FIELD_ENCRYPTION_KEY_OLD", "")
        if old_key:
            try:
                return _fernet_for(old_key).decrypt(token).decode("utf-8")
            except InvalidToken:
                pass
        raise EncryptionError(
            "Entschlüsselung fehlgeschlagen (falscher Schlüssel oder manipulierte Daten)."
        ) from None


class EncryptedTextField(models.TextField):
    description = "Feldverschlüsselter Text (Fernet, at-rest)"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == "" or is_encrypted(value):
            return value
        return encrypt_text(str(value))

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        if not is_encrypted(value):
            return value
        return decrypt_text(value)

    def to_python(self, value):
        if value is None or value == "":
            return value
        if is_encrypted(value):
            return decrypt_text(value)
        return value
