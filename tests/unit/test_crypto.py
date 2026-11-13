import pytest
from django.db import connection, models

from apps.core.crypto import (
    ENCRYPTED_PREFIX,
    EncryptedTextField,
    decrypt_text,
    encrypt_text,
    is_encrypted,
)

pytestmark = pytest.mark.django_db


def test_encrypt_roundtrip():
    ciphertext = encrypt_text("Nur für uns")
    assert is_encrypted(ciphertext)
    assert ciphertext.startswith(ENCRYPTED_PREFIX)
    assert "Nur für uns" not in ciphertext
    assert decrypt_text(ciphertext) == "Nur für uns"


def test_plaintext_passthrough():
    assert decrypt_text("Klartext") == "Klartext"
    assert not is_encrypted("Klartext")


@pytest.mark.django_db(transaction=True)
def test_field_stores_ciphertext_at_rest():
    class ProbeSecret(models.Model):
        value = EncryptedTextField()

        class Meta:
            app_label = "core"

        def __str__(self) -> str:
            return str(self.pk)

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(ProbeSecret)
    try:
        ProbeSecret.objects.create(value="geheime Antwort")
        with connection.cursor() as cursor:
            cursor.execute("SELECT value FROM core_probesecret")
            stored = cursor.fetchone()[0]
        assert stored.startswith(ENCRYPTED_PREFIX)
        assert "geheime Antwort" not in stored
        assert ProbeSecret.objects.get().value == "geheime Antwort"
    finally:
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(ProbeSecret)
