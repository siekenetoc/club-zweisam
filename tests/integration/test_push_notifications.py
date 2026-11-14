import pytest
from django.contrib.auth.models import Group
from django.db import connection
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER
from apps.clubroom.services import create_clubroom
from apps.feed.delivery import send_via_channel
from apps.feed.models import (
    EVENT_CHECKIN_CREATED,
    PROVIDER_ELEMENT,
    PROVIDER_GOTIFY,
    PROVIDER_SIGNAL,
    PROVIDER_TELEGRAM,
    PROVIDER_WHATSAPP,
    Notification,
    NotificationChannel,
    NotificationSubscription,
)
from apps.feed.services import record_event
from apps.lounge.services import set_safe_mode
from apps.wishes.services import create_wish

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


def make_channel(clubroom, provider=PROVIDER_TELEGRAM, config=None, label="Kanal"):
    channel = NotificationChannel.objects.create(
        clubroom=clubroom, provider=provider, label=label, is_enabled=True
    )
    channel.set_config(
        config if config is not None else {"bot_token": "123:secret", "default_target": "42"}
    )
    channel.save()
    return channel


def subscribe(channel, user, destination=""):
    return NotificationSubscription.objects.create(
        channel=channel, user=user, destination=destination
    )


def test_contentless_push_via_telegram(monkeypatch, django_capture_on_commit_callbacks):
    clubroom, anna, bea = make_room()
    channel = make_channel(clubroom)
    subscribe(channel, bea)
    calls = []
    monkeypatch.setattr(
        "apps.feed.delivery._http_json",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    with override_settings(PORTAL_BASE_URL="https://portal.example"):
        with django_capture_on_commit_callbacks(execute=True):
            record_event(
                clubroom=clubroom,
                event_type=EVENT_CHECKIN_CREATED,
                actor=anna,
            )
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[0] == "POST"
    assert "api.telegram.org" in args[1]
    payload = args[2]
    text = payload["text"]
    assert "https://portal.example/lounge/" in text
    assert "checkin" not in text.lower()
    assert payload["chat_id"] == "42"


def test_secret_content_never_reaches_channel(monkeypatch, django_capture_on_commit_callbacks):
    clubroom, anna, bea = make_room()
    channel = make_channel(clubroom)
    subscribe(channel, bea)
    calls = []
    monkeypatch.setattr(
        "apps.feed.delivery._http_json",
        lambda *args, **kwargs: calls.append(args),
    )
    with django_capture_on_commit_callbacks(execute=True):
        create_wish(
            clubroom=clubroom,
            user=anna,
            wish_type="fantasie",
            title="Titel GEHEIM",
            body="Inhalt GEHEIM",
        )
    assert calls
    serialized = str(calls)
    assert "GEHEIM" not in serialized
    assert "wish" not in serialized.lower()


def test_safe_mode_queues_and_delivers_later(monkeypatch, django_capture_on_commit_callbacks):
    clubroom, anna, bea = make_room()
    channel = make_channel(clubroom)
    subscribe(channel, bea)
    calls = []
    monkeypatch.setattr(
        "apps.feed.delivery._http_json",
        lambda *args, **kwargs: calls.append(args),
    )
    bea.is_safe_mode_active = True
    bea.save(update_fields=["is_safe_mode_active"])
    with django_capture_on_commit_callbacks(execute=True):
        record_event(clubroom=clubroom, event_type=EVENT_CHECKIN_CREATED, actor=anna)
    assert calls == []
    queued = Notification.objects.get(user=bea)
    assert queued.delivered_at is None

    set_safe_mode(user=bea, active=False)
    assert len(calls) == 1
    queued.refresh_from_db()
    assert queued.delivered_at is not None


def test_disabled_channel_or_subscription_does_not_send(
    monkeypatch, django_capture_on_commit_callbacks
):
    clubroom, anna, bea = make_room()
    channel = make_channel(clubroom)
    subscription = subscribe(channel, bea)
    calls = []
    monkeypatch.setattr(
        "apps.feed.delivery._http_json",
        lambda *args, **kwargs: calls.append(args),
    )
    channel.is_enabled = False
    channel.save(update_fields=["is_enabled"])
    with django_capture_on_commit_callbacks(execute=True):
        record_event(clubroom=clubroom, event_type=EVENT_CHECKIN_CREATED, actor=anna)
    assert calls == []

    channel.is_enabled = True
    channel.save(update_fields=["is_enabled"])
    subscription.is_enabled = False
    subscription.save(update_fields=["is_enabled"])
    with django_capture_on_commit_callbacks(execute=True):
        record_event(clubroom=clubroom, event_type=EVENT_CHECKIN_CREATED, actor=anna)
    assert calls == []


def test_send_failure_does_not_break_notification(monkeypatch, django_capture_on_commit_callbacks):
    clubroom, anna, bea = make_room()
    channel = make_channel(clubroom)
    subscribe(channel, bea)
    monkeypatch.setattr(
        "apps.feed.delivery._http_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("offline")),
    )
    with django_capture_on_commit_callbacks(execute=True):
        record_event(clubroom=clubroom, event_type=EVENT_CHECKIN_CREATED, actor=anna)
    assert Notification.objects.filter(user=bea, delivered_at__isnull=False).exists()


def test_channel_secrets_and_destinations_are_encrypted_at_rest():
    clubroom, anna, bea = make_room()
    channel = make_channel(clubroom, config={"bot_token": "GEHEIM", "default_target": "42"})
    subscribe(channel, bea, destination="MEINE-CHAT-ID")
    with connection.cursor() as cursor:
        cursor.execute("SELECT config FROM feed_notificationchannel WHERE id = %s", [channel.pk])
        stored_config = cursor.fetchone()[0]
        cursor.execute(
            "SELECT destination FROM feed_notificationsubscription WHERE channel_id = %s",
            [channel.pk],
        )
        stored_destination = cursor.fetchone()[0]
    assert stored_config.startswith("enc:v1:")
    assert "GEHEIM" not in stored_config
    assert stored_destination.startswith("enc:v1:")
    assert "MEINE-CHAT-ID" not in stored_destination


@pytest.mark.parametrize(
    "provider,config,expected_url,expected_payload",
    [
        (
            PROVIDER_WHATSAPP,
            {
                "access_token": "token",
                "phone_number_id": "123",
                "api_version": "v22.0",
            },
            "graph.facebook.com/v22.0/123/messages",
            {"messaging_product": "whatsapp", "type": "text"},
        ),
        (
            PROVIDER_TELEGRAM,
            {"bot_token": "bot", "default_target": "42"},
            "api.telegram.org/botbot/sendMessage",
            {"chat_id": "42"},
        ),
        (
            PROVIDER_SIGNAL,
            {"api_url": "http://signal:8080", "sender_number": "+491"},
            "http://signal:8080/v2/send",
            {"recipients": ["+492"]},
        ),
        (
            PROVIDER_ELEMENT,
            {"homeserver_url": "https://matrix.example", "access_token": "tok"},
            "matrix.example/_matrix/client/v3/rooms/%21raum%3Aexample/send/m.room.message/",
            {"msgtype": "m.text"},
        ),
        (
            PROVIDER_GOTIFY,
            {"server_url": "https://gotify.example", "app_token": "app"},
            "gotify.example/message?token=",
            {"title": "Club Zweisam"},
        ),
    ],
)
def test_provider_payloads(monkeypatch, provider, config, expected_url, expected_payload):
    clubroom, _, _ = make_room()
    channel = make_channel(clubroom, provider=provider, config=config)
    calls = []
    monkeypatch.setattr(
        "apps.feed.delivery._http_json",
        lambda *args, **kwargs: calls.append(args),
    )
    destinations = {
        PROVIDER_WHATSAPP: "+491",
        PROVIDER_TELEGRAM: "42",
        PROVIDER_SIGNAL: "+492",
        PROVIDER_ELEMENT: "!raum:example",
        PROVIDER_GOTIFY: "",
    }
    destination = destinations[provider]
    assert send_via_channel(channel, destination) is True
    method, url, payload = calls[0]
    assert expected_url in url
    for key, value in expected_payload.items():
        assert payload[key] == value
    assert "Club Zweisam" in str(payload)
    assert "/lounge/" in str(payload)


def test_lounge_subscription_ui(client):
    clubroom, anna, _ = make_room()
    channel = make_channel(clubroom, config={"bot_token": "bot", "default_target": "42"})
    client.force_login(anna)
    content = client.get(reverse("lounge:index")).content.decode()
    assert "Push-Benachrichtigungen" in content
    assert channel.label in content

    response = client.post(
        reverse("lounge:notification_subscription"),
        {"channel_id": channel.pk, "action": "enable", "destination": ""},
    )
    assert response.status_code == 302
    subscription = NotificationSubscription.objects.get(channel=channel, user=anna)
    assert subscription.is_enabled is True

    client.post(
        reverse("lounge:notification_subscription"),
        {"channel_id": channel.pk, "action": "disable"},
    )
    subscription.refresh_from_db()
    assert subscription.is_enabled is False


def test_non_http_channel_target_is_rejected(monkeypatch):
    clubroom, _, _ = make_room()
    channel = make_channel(
        clubroom,
        provider=PROVIDER_GOTIFY,
        config={"server_url": "file:///etc/passwd", "app_token": "app"},
    )
    calls = []
    monkeypatch.setattr(
        "apps.feed.delivery._http_json",
        lambda *args, **kwargs: calls.append(args),
    )
    assert send_via_channel(channel, "") is False
    assert calls == []


def test_push_test_command(monkeypatch):
    from django.core.management import call_command

    clubroom, _, _ = make_room()
    channel = make_channel(clubroom)
    calls = []
    monkeypatch.setattr(
        "apps.feed.delivery._http_json",
        lambda *args, **kwargs: calls.append(args),
    )
    call_command("push_test", channel=channel.pk)
    assert len(calls) == 1


def test_admin_can_create_channel(client):
    clubroom, anna, _ = make_room()
    anna.is_superuser = True
    anna.is_staff = True
    anna.save(update_fields=["is_superuser", "is_staff"])
    client.force_login(anna)
    response = client.post(
        reverse("admin:feed_notificationchannel_add"),
        {
            "clubroom": clubroom.pk,
            "provider": "telegram",
            "label": "Admin-Kanal",
            "config": '{"bot_token": "bot", "default_target": "42"}',
            "is_enabled": "on",
        },
    )
    assert response.status_code == 302
    channel = NotificationChannel.objects.get(label="Admin-Kanal")
    assert channel.get_config()["bot_token"] == "bot"
    assert channel.is_enabled is True


def _platform_admin():
    user = User.objects.create_user(
        username="platform",
        email="platform@example.com",
        password="sehr-geheim-1234",
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name="Plattform-Admin")
    user.groups.add(group)
    return user


def test_messenger_setup_is_platform_admin_only(client):
    clubroom, _, _ = make_room()
    staff = User.objects.create_user(
        username="staff",
        email="staff@example.com",
        password="sehr-geheim-1234",
        is_staff=True,
    )
    client.force_login(staff)
    assert client.get(reverse("admin_panel:messenger_setup")).status_code == 403

    client.force_login(_platform_admin())
    response = client.get(reverse("admin_panel:messenger_setup"))
    assert response.status_code == 200
    assert "Messenger einrichten" in response.content.decode()


def test_messenger_setup_creates_telegram_channel(client):
    clubroom, _, _ = make_room()
    client.force_login(_platform_admin())
    response = client.post(
        reverse("admin_panel:messenger_setup"),
        {
            "clubroom": clubroom.pk,
            "provider": "telegram",
            "label": "Wizard Telegram",
            "default_target": "42",
            "is_enabled": "on",
            "telegram_bot_token": "123:secret",
        },
    )
    assert response.status_code == 302
    channel = NotificationChannel.objects.get(label="Wizard Telegram")
    assert channel.provider == "telegram"
    assert channel.get_config()["bot_token"] == "123:secret"
    assert channel.is_enabled is True


def test_telegram_chat_discovery(monkeypatch, client):
    clubroom, _, _ = make_room()
    monkeypatch.setattr(
        "apps.admin_panel.views.discover_chats",
        lambda token: [
            {"id": -1001234567890, "type": "supergroup", "title": "Jana und Olli", "username": ""}
        ],
    )
    client.force_login(_platform_admin())
    response = client.post(
        reverse("admin_panel:messenger_setup"),
        {
            "provider": "telegram",
            "telegram_bot_token": "123:secret",
            "action": "telegram_discover",
        },
    )
    assert response.status_code == 200
    assert "ID -1001234567890 übernehmen" in response.content.decode()


def test_messenger_setup_requires_provider_fields(client):
    clubroom, _, _ = make_room()
    client.force_login(_platform_admin())
    response = client.post(
        reverse("admin_panel:messenger_setup"),
        {
            "clubroom": clubroom.pk,
            "provider": "whatsapp",
            "label": "Kaputt",
            "is_enabled": "on",
        },
    )
    assert response.status_code == 200
    assert "Pflichtfeld für WhatsApp" in response.content.decode()
    assert not NotificationChannel.objects.filter(label="Kaputt").exists()


def test_messenger_setup_test_action(monkeypatch, client):
    clubroom, _, _ = make_room()
    channel = make_channel(clubroom)
    calls = []
    monkeypatch.setattr(
        "apps.feed.delivery._http_json",
        lambda *args, **kwargs: calls.append(args),
    )
    client.force_login(_platform_admin())
    response = client.post(
        reverse("admin_panel:messenger_setup"),
        {"channel_id": channel.pk, "action": "test"},
        follow=True,
    )
    assert response.status_code == 200
    assert "Testnachricht gesendet" in response.content.decode()
    assert len(calls) == 1


def test_channel_requires_platform_admin(client):
    clubroom, _, _ = make_room()
    make_channel(clubroom)
    staff = User.objects.create_user(
        username="staff",
        email="staff@example.com",
        password="sehr-geheim-1234",
        is_staff=True,
    )
    client.force_login(staff)
    assert client.get(reverse("admin:feed_notificationchannel_changelist")).status_code == 403

    platform = User.objects.create_user(
        username="platform",
        email="platform@example.com",
        password="sehr-geheim-1234",
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name="Plattform-Admin")
    platform.groups.add(group)
    client.force_login(platform)
    assert client.get(reverse("admin:feed_notificationchannel_changelist")).status_code == 200
