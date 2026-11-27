import re

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.accounts.models import User
from apps.clubroom.models import Membership
from apps.clubroom.permissions import ADVISOR, GUEST, MEDIATOR, OWNER
from apps.clubroom.services import create_clubroom
from apps.crisis.services import (
    active_crisis_session,
    end_crisis_session,
    start_crisis_session,
)
from apps.deep_talk.models import (
    MODE_CRISIS,
    MODE_REPAIR,
    MODE_TALK,
    TalkPrompt,
    TalkSession,
)
from apps.deep_talk.services import (
    active_session,
    end_session,
    pause_session,
    resume_session,
    start_session,
    toggle_prompt,
)
from apps.feed.models import FeedEvent, Notification

pytestmark = pytest.mark.django_db


def make_room():
    anna = User.objects.create_user(
        username="anna", email="anna@example.com", password="sehr-geheim-1234"
    )
    bea = User.objects.create_user(
        username="bea", email="bea@example.com", password="sehr-geheim-1234"
    )
    clubroom = create_clubroom(user=anna, name="Unser Raum", safe_word="Anker")
    Membership.objects.create(clubroom=clubroom, user=bea, role=OWNER)
    return clubroom, anna, bea


def test_start_talk_creates_prompts_and_is_idempotent():
    clubroom, anna, _ = make_room()
    session = start_session(clubroom=clubroom, user=anna, mode=MODE_TALK)
    assert session.mode == MODE_TALK
    assert session.prompts.count() == 6
    assert session.prompts.filter(text__icontains="Was brauchst du").exists()

    again = start_session(clubroom=clubroom, user=anna, mode=MODE_TALK)
    assert again.pk == session.pk
    assert TalkPrompt.objects.count() == 6


def test_repair_session_is_separate_from_talk():
    clubroom, anna, bea = make_room()
    talk = start_session(clubroom=clubroom, user=anna, mode=MODE_TALK)
    repair = start_session(clubroom=clubroom, user=bea, mode=MODE_REPAIR)
    assert talk.pk != repair.pk
    assert active_session(clubroom, MODE_TALK) == talk
    assert active_session(clubroom, MODE_REPAIR) == repair
    assert repair.prompts.filter(text__icontains="verletzt").exists()


def test_only_deep_talk_roles_can_access(client):
    clubroom, anna, _ = make_room()
    guest = User.objects.create_user(
        username="gast", email="gast@example.com", password="sehr-geheim-1234"
    )
    advisor = User.objects.create_user(
        username="beratung", email="beratung@example.com", password="sehr-geheim-1234"
    )
    mediator = User.objects.create_user(
        username="mediation", email="mediation@example.com", password="sehr-geheim-1234"
    )
    Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    Membership.objects.create(clubroom=clubroom, user=advisor, role=ADVISOR)
    Membership.objects.create(clubroom=clubroom, user=mediator, role=MEDIATOR)

    client.force_login(guest)
    assert client.get(reverse("deep_talk:index")).status_code == 403
    client.force_login(advisor)
    assert client.get(reverse("deep_talk:index")).status_code == 200
    client.force_login(mediator)
    assert client.get(reverse("deep_talk:index")).status_code == 200


def test_toggle_prompt_timeout_and_resume():
    clubroom, anna, bea = make_room()
    session = start_session(clubroom=clubroom, user=anna, mode=MODE_TALK)
    prompt = session.prompts.first()
    toggle_prompt(session=session, prompt_id=prompt.pk, user=bea)
    prompt.refresh_from_db()
    assert prompt.answered is True

    pause_session(session=session, user=bea)
    session.refresh_from_db()
    assert session.is_paused is True
    assert session.timeout_by == bea

    resume_session(session=session, user=anna)
    session.refresh_from_db()
    assert session.is_paused is False
    assert session.timeout_by is None


def test_ended_session_is_read_only_and_can_restart():
    clubroom, anna, bea = make_room()
    session = start_session(clubroom=clubroom, user=anna, mode=MODE_TALK)
    prompt = session.prompts.first()
    end_session(session=session, user=bea)
    session.refresh_from_db()
    assert session.ended_at is not None
    with pytest.raises(ValidationError):
        toggle_prompt(session=session, prompt_id=prompt.pk, user=anna)
    assert active_session(clubroom, MODE_TALK) is None
    new_session = start_session(clubroom=clubroom, user=anna, mode=MODE_TALK)
    assert new_session.pk != session.pk


def test_deep_talk_creates_no_feed_events_or_notifications():
    clubroom, anna, bea = make_room()
    before_events = FeedEvent.objects.count()
    before_notifications = Notification.objects.count()
    session = start_session(clubroom=clubroom, user=anna, mode=MODE_REPAIR)
    toggle_prompt(session=session, prompt_id=session.prompts.first().pk, user=bea)
    pause_session(session=session, user=bea)
    resume_session(session=session, user=anna)
    end_session(session=session, user=bea)
    assert FeedEvent.objects.count() == before_events
    assert Notification.objects.count() == before_notifications


def test_deep_talk_page_has_no_free_chat(client):
    clubroom, anna, _ = make_room()
    session = start_session(clubroom=clubroom, user=anna, mode=MODE_TALK)
    client.force_login(anna)
    content = client.get(reverse("deep_talk:session", kwargs={"pk": session.pk})).content.decode()
    assert "<textarea" not in content
    assert "Leitfragen" in content


def test_crisis_is_a_separate_module_with_hard_references(client):
    clubroom, anna, _ = make_room()
    client.force_login(anna)
    response = client.get(reverse("crisis:index"))
    content = response.content.decode()
    assert response.status_code == 200
    assert "Notruf" in content
    assert "112" in content
    assert "Telefonseelsorge" in content
    assert "116 016" in content
    main = re.search(r"<main[^>]*>(.*?)</main>", content, re.S).group(1)
    assert "keine Bewertung" in main
    assert "Challenge" not in main
    assert "Punkte" not in main


def test_crisis_session_has_no_prompts_and_no_side_effects():
    clubroom, anna, bea = make_room()
    before_events = FeedEvent.objects.count()
    before_notifications = Notification.objects.count()
    session = start_crisis_session(clubroom=clubroom, user=bea)
    assert session.mode == MODE_CRISIS
    assert session.prompts.count() == 0
    assert active_crisis_session(clubroom) == session
    again = start_crisis_session(clubroom=clubroom, user=anna)
    assert again.pk == session.pk
    end_crisis_session(session=session, user=anna)
    session.refresh_from_db()
    assert session.ended_at is not None
    assert FeedEvent.objects.count() == before_events
    assert Notification.objects.count() == before_notifications
    assert TalkSession.objects.filter(mode=MODE_CRISIS).count() == 1


def test_crisis_does_not_appear_in_deep_talk_history(client):
    clubroom, anna, _ = make_room()
    crisis = start_crisis_session(clubroom=clubroom, user=anna)
    client.force_login(anna)
    content = client.get(reverse("deep_talk:index")).content.decode()
    assert f"/deep-talk/{crisis.pk}/" not in content


def test_guest_can_open_crisis_room(client):
    clubroom, anna, _ = make_room()
    guest = User.objects.create_user(
        username="gast", email="gast@example.com", password="sehr-geheim-1234"
    )
    Membership.objects.create(clubroom=clubroom, user=guest, role=GUEST)
    client.force_login(guest)
    assert client.get(reverse("crisis:index")).status_code == 200
    response = client.post(reverse("crisis:start"))
    assert response.status_code == 302
    assert active_crisis_session(clubroom) is not None


def test_crisis_mode_cannot_be_started_via_deep_talk():
    clubroom, anna, _ = make_room()
    with pytest.raises(ValidationError):
        start_session(clubroom=clubroom, user=anna, mode=MODE_CRISIS)
