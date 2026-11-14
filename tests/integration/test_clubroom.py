import re

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.clubroom.models import Clubroom, Invitation, Membership
from apps.clubroom.permissions import (
    ADVISOR,
    GUEST,
    MEDIATOR,
    MODERATOR,
    MODULES,
    OWNER,
    SEX_PARTNER,
    default_permissions_for,
)
from apps.clubroom.services import create_clubroom

pytestmark = pytest.mark.django_db


def make_user(username, email):
    return User.objects.create_user(username=username, email=email, password="sehr-geheim-1234")


def make_clubroom(user):
    return create_clubroom(user=user, name="Unser Raum", safe_word="Anker")


def extract_token(message_body):
    match = re.search(r"/einladung/([A-Za-z0-9_\-]+)/", message_body)
    assert match is not None
    return match.group(1)


def test_create_clubroom_makes_owner(client):
    user = make_user("anna", "anna@example.com")
    client.force_login(user)

    response = client.post(
        reverse("clubroom:create"),
        {"name": "Unser Raum", "rules": "Nur wir.", "safe_word": "Anker"},
        follow=True,
    )
    assert response.status_code == 200
    assert "Anker" not in response.content.decode()

    clubroom = Clubroom.objects.get()
    assert clubroom.created_by == user
    assert clubroom.safe_word == "Anker"
    membership = Membership.objects.get(user=user, clubroom=clubroom)
    assert membership.role == OWNER
    assert membership.is_active
    assert all(membership.has_module_access(module) for module in MODULES)


def test_invite_and_accept_flow(client):
    owner = make_user("anna", "anna@example.com")
    partner = make_user("bea", "bea@example.com")
    clubroom = make_clubroom(owner)
    client.force_login(owner)

    response = client.post(
        reverse("clubroom:invite"),
        {"email": "bea@example.com", "role": OWNER},
    )
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert "Anker" not in mail.outbox[0].body
    assert "So nimmst du teil" in mail.outbox[0].body
    assert "Einladung von" in mail.outbox[0].subject
    assert "https://club-zweisam.localhost/einladung/" in mail.outbox[0].body

    invitation = Invitation.objects.get()
    assert invitation.email == "bea@example.com"
    raw_token = extract_token(mail.outbox[0].body)
    assert invitation.token_hash != raw_token
    assert raw_token not in invitation.token_hash
    assert invitation.is_pending

    client.force_login(partner)
    response = client.post(reverse("clubroom:invitation_accept", kwargs={"token": raw_token}))
    assert response.status_code == 302

    membership = Membership.objects.get(user=partner, clubroom=clubroom)
    assert membership.role == OWNER
    assert membership.invited_by == owner
    invitation.refresh_from_db()
    assert invitation.accepted_at is not None


def test_resend_invitation_rotates_token(client):
    owner = make_user("anna", "anna@example.com")
    partner = make_user("bea", "bea@example.com")
    make_clubroom(owner)
    client.force_login(owner)
    client.post(reverse("clubroom:invite"), {"email": "bea@example.com", "role": GUEST})
    invitation = Invitation.objects.get()
    old_token = extract_token(mail.outbox[0].body)

    response = client.post(reverse("clubroom:invitation_resend", kwargs={"pk": invitation.pk}))
    assert response.status_code == 302
    assert len(mail.outbox) == 2
    new_token = extract_token(mail.outbox[1].body)
    assert new_token != old_token
    invitation.refresh_from_db()
    assert invitation.token_hash != __import__(
        "apps.clubroom.models", fromlist=["hash_token"]
    ).hash_token(old_token)
    assert "So nimmst du teil" in mail.outbox[1].body

    client.force_login(partner)
    client.post(reverse("clubroom:invitation_accept", kwargs={"token": old_token}))
    assert not Membership.objects.filter(user=partner).exists()
    client.post(reverse("clubroom:invitation_accept", kwargs={"token": new_token}))
    assert Membership.objects.filter(user=partner, role=GUEST).exists()


def test_invitation_link_shows_login_or_register_for_anonymous(client):
    owner = make_user("anna", "anna@example.com")
    make_clubroom(owner)
    client.force_login(owner)
    client.post(reverse("clubroom:invite"), {"email": "bea@example.com", "role": GUEST})
    token = extract_token(mail.outbox[0].body)
    client.logout()
    response = client.get(reverse("clubroom:invitation_accept", kwargs={"token": token}))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Anmelden" in content
    assert "Konto anlegen" in content
    assert "bea@example.com" in content


def test_invitation_email_is_bound(client):
    owner = make_user("anna", "anna@example.com")
    make_user("bea", "bea@example.com")
    intruder = make_user("cora", "cora@example.com")
    make_clubroom(owner)
    client.force_login(owner)
    client.post(reverse("clubroom:invite"), {"email": "bea@example.com", "role": GUEST})
    token = extract_token(mail.outbox[0].body)

    client.force_login(intruder)
    response = client.post(
        reverse("clubroom:invitation_accept", kwargs={"token": token}),
        follow=True,
    )
    assert response.status_code == 200
    assert not Membership.objects.filter(user=intruder).exists()


def test_revoked_invitation_cannot_be_accepted(client):
    owner = make_user("anna", "anna@example.com")
    partner = make_user("bea", "bea@example.com")
    make_clubroom(owner)
    client.force_login(owner)
    client.post(reverse("clubroom:invite"), {"email": "bea@example.com", "role": GUEST})
    invitation = Invitation.objects.get()
    token = extract_token(mail.outbox[0].body)

    response = client.post(reverse("clubroom:invitation_revoke", kwargs={"pk": invitation.pk}))
    assert response.status_code == 302
    invitation.refresh_from_db()
    assert invitation.revoked_at is not None

    client.force_login(partner)
    response = client.post(
        reverse("clubroom:invitation_accept", kwargs={"token": token}), follow=True
    )
    assert response.status_code == 200
    assert not Membership.objects.filter(user=partner).exists()


def test_expired_invitation_cannot_be_accepted(client):
    owner = make_user("anna", "anna@example.com")
    partner = make_user("bea", "bea@example.com")
    make_clubroom(owner)
    client.force_login(owner)
    client.post(reverse("clubroom:invite"), {"email": "bea@example.com", "role": GUEST})
    invitation = Invitation.objects.get()
    token = extract_token(mail.outbox[0].body)
    Invitation.objects.filter(pk=invitation.pk).update(
        expires_at=timezone.now() - timezone.timedelta(minutes=1)
    )

    client.force_login(partner)
    client.post(reverse("clubroom:invitation_accept", kwargs={"token": token}))
    assert not Membership.objects.filter(user=partner).exists()


def test_unknown_token_is_not_revealed(client):
    user = make_user("bea", "bea@example.com")
    client.force_login(user)
    response = client.get(reverse("clubroom:invitation_accept", kwargs={"token": "unbekannt"}))
    assert response.status_code == 404


def test_only_two_owners(client):
    owner = make_user("anna", "anna@example.com")
    partner = make_user("bea", "bea@example.com")
    make_clubroom(owner)
    client.force_login(owner)

    client.post(reverse("clubroom:invite"), {"email": "bea@example.com", "role": OWNER})
    token = extract_token(mail.outbox[0].body)
    assert Invitation.objects.count() == 1

    response = client.post(
        reverse("clubroom:invite"),
        {"email": "cora@example.com", "role": OWNER},
    )
    assert response.status_code == 200
    assert Invitation.objects.count() == 1
    assert "höchstens zwei Hauptmitglieder" in response.content.decode()

    client.force_login(partner)
    client.post(reverse("clubroom:invitation_accept", kwargs={"token": token}))
    clubroom = Clubroom.objects.get()
    assert clubroom.active_owners().count() == 2

    client.force_login(owner)
    response = client.post(
        reverse("clubroom:invite"),
        {"email": "dora@example.com", "role": OWNER},
    )
    assert response.status_code == 200
    assert Invitation.objects.filter(email="dora@example.com").count() == 0


def test_owner_can_edit_clubroom_settings(client):
    owner = make_user("anna", "anna@example.com")
    partner = make_user("bea", "bea@example.com")
    clubroom = make_clubroom(owner)
    Membership.objects.create(clubroom=clubroom, user=partner, role=GUEST)
    client.force_login(owner)
    response = client.get(reverse("clubroom:settings"))
    assert response.status_code == 200
    response = client.post(
        reverse("clubroom:settings"),
        {
            "name": "Neuer Name",
            "rules": "Neue Regel.",
            "safe_word": "NeuesWort",
        },
    )
    assert response.status_code == 302
    clubroom.refresh_from_db()
    assert clubroom.name == "Neuer Name"
    assert clubroom.rules == "Neue Regel."
    assert clubroom.safe_word == "NeuesWort"

    client.force_login(partner)
    assert client.get(reverse("clubroom:settings")).status_code == 403


def test_non_owner_cannot_invite(client):
    owner = make_user("anna", "anna@example.com")
    guest = make_user("bea", "bea@example.com")
    clubroom = make_clubroom(owner)
    Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    client.force_login(guest)

    response = client.get(reverse("clubroom:invite"))
    assert response.status_code == 403


def test_role_permissions_matrix():
    assert all(default_permissions_for(OWNER).values())
    moderator = default_permissions_for(MODERATOR)
    assert moderator["lounge"] and moderator["feed"]
    assert not moderator["deep_talk"]
    assert not moderator["roulette"]
    assert default_permissions_for(ADVISOR)["deep_talk"]
    assert default_permissions_for(MEDIATOR)["deep_talk"]
    assert default_permissions_for(SEX_PARTNER)["playbook"]
    assert not default_permissions_for(GUEST)["roulette"]


def test_guest_is_read_only(client):
    owner = make_user("anna", "anna@example.com")
    guest = make_user("bea", "bea@example.com")
    clubroom = make_clubroom(owner)
    membership = Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)

    assert membership.has_module_access("lounge")
    assert not membership.can_write_module("lounge")
    assert not membership.has_module_access("wishes")


def test_membership_revocation_is_immediate(client):
    owner = make_user("anna", "anna@example.com")
    guest = make_user("bea", "bea@example.com")
    clubroom = make_clubroom(owner)
    membership = Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    client.force_login(owner)

    response = client.post(reverse("clubroom:membership_revoke", kwargs={"pk": membership.pk}))
    assert response.status_code == 302
    membership.refresh_from_db()
    assert membership.revoked_at is not None

    client.force_login(guest)
    response = client.get(reverse("clubroom:home"))
    assert response.status_code == 200
    assert "Noch kein Clubraum" in response.content.decode()


def test_owner_cannot_be_removed(client):
    owner = make_user("anna", "anna@example.com")
    partner = make_user("bea", "bea@example.com")
    clubroom = make_clubroom(owner)
    membership = Membership.objects.create(clubroom=clubroom, user=partner, role=OWNER)
    client.force_login(owner)

    client.post(reverse("clubroom:membership_revoke", kwargs={"pk": membership.pk}))
    membership.refresh_from_db()
    assert membership.revoked_at is None


def test_user_cannot_join_second_clubroom(client):
    owner = make_user("anna", "anna@example.com")
    other_owner = make_user("bea", "bea@example.com")
    make_clubroom(owner)
    make_clubroom(other_owner)
    client.force_login(owner)

    response = client.get(reverse("clubroom:create"))
    assert response.status_code == 302


def test_security_lifecycle_is_audited(client):
    from apps.core.audit import AuditEntry

    owner = make_user("anna", "anna@example.com")
    partner = make_user("bea", "bea@example.com")
    make_clubroom(owner)
    client.force_login(owner)
    client.post(reverse("clubroom:invite"), {"email": "bea@example.com", "role": GUEST})
    token = extract_token(mail.outbox[0].body)
    invitation = Invitation.objects.get()
    client.post(reverse("clubroom:invitation_revoke", kwargs={"pk": invitation.pk}))
    client.post(reverse("clubroom:invite"), {"email": "bea@example.com", "role": GUEST})
    token = extract_token(mail.outbox[1].body)

    client.force_login(partner)
    client.post(reverse("clubroom:invitation_accept", kwargs={"token": token}))

    actions = list(AuditEntry.objects.order_by("id").values_list("action", flat=True))
    assert actions == [
        "clubroom.create",
        "invitation.create",
        "invitation.revoke",
        "invitation.create",
        "invitation.accept",
    ]
    ok, broken_pk, reason = AuditEntry.verify_chain()
    assert ok is True
    assert broken_pk is None
