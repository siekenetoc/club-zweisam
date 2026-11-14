import pytest
from django.db.models import ProtectedError

from apps.accounts.models import User
from apps.core.audit import (
    GENESIS_HASH,
    AuditAppendOnlyError,
    AuditEntry,
)

pytestmark = pytest.mark.django_db


def test_chain_is_linked_and_valid():
    first = AuditEntry.objects.create(action="login", target_type="accounts.user", target_id="1")
    second = AuditEntry.objects.create(action="view", target_type="accounts.user", target_id="1")
    assert first.prev_hash == GENESIS_HASH
    assert second.prev_hash == first.hash
    ok, broken_pk, reason = AuditEntry.verify_chain()
    assert ok is True
    assert broken_pk is None
    assert reason == ""


def test_append_only_blocks_update_and_delete():
    entry = AuditEntry.objects.create(action="login")
    with pytest.raises(AuditAppendOnlyError):
        entry.save()
    with pytest.raises(AuditAppendOnlyError):
        entry.delete()


def test_tampering_breaks_chain():
    entry = AuditEntry.objects.create(action="login", reason="original")
    AuditEntry.objects.filter(pk=entry.pk).update(reason="manipuliert")
    ok, broken_pk, reason = AuditEntry.verify_chain()
    assert ok is False
    assert broken_pk == entry.pk
    assert reason == "hash"


def test_metadata_is_part_of_hash():
    entry = AuditEntry.objects.create(action="login", metadata={"role": "moderator"})
    entry.metadata["role"] = "admin"
    assert entry.hash != entry.compute_hash(entry.prev_hash)


def test_actor_with_audit_entries_cannot_be_deleted():
    user = User.objects.create_user(
        username="audit-actor", email="audit-actor@example.com", password="sehr-geheim-1234"
    )
    AuditEntry.objects.create(actor=user, action="login")
    with pytest.raises(ProtectedError):
        user.delete()
