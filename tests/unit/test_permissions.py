import pytest

from apps.core.models import AuditEntry
from apps.core.permissions import is_sensitive_label, is_sensitive_model

pytestmark = pytest.mark.django_db


def test_sensitive_labels():
    assert is_sensitive_label("roulette.SecretAnswer")
    assert is_sensitive_label("wishes.fantasywish")
    assert not is_sensitive_label("accounts.user")


def test_sensitive_model_detection():
    assert not is_sensitive_model(AuditEntry)
