import json
import logging
import ssl
import urllib.error
import urllib.parse
import urllib.request
import uuid

from django.conf import settings

from apps.feed.models import (
    PROVIDER_ELEMENT,
    PROVIDER_GOTIFY,
    PROVIDER_SIGNAL,
    PROVIDER_TELEGRAM,
    PROVIDER_WHATSAPP,
    NotificationChannel,
    NotificationSubscription,
    PersonalNotificationChannel,
    notification_allowed,
)

logger = logging.getLogger(__name__)


def portal_url() -> str:
    base = getattr(settings, "PORTAL_BASE_URL", "https://club-zweisam.localhost")
    return f"{base.rstrip('/')}/lounge/"


def notification_text() -> str:
    return f"Club Zweisam: Neues Ereignis im Portal. {portal_url()}"


def _http_json(method, url, payload, headers=None, insecure=False):
    if urllib.parse.urlparse(url).scheme not in {"http", "https"}:
        raise ValueError("Nur HTTP(S)-Ziele erlaubt")
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method=method,
    )
    context = ssl._create_unverified_context() if insecure else None  # nosec B323
    with urllib.request.urlopen(request, timeout=5, context=context) as response:  # nosec B310
        response.read()


def _required(config, keys):
    missing = [key for key in keys if not config.get(key)]
    if missing:
        raise ValueError("fehlende Kanal-Konfiguration")
    return config


def _config_url(config, key):
    value = config.get(key)
    if urllib.parse.urlparse(value or "").scheme not in {"http", "https"}:
        raise ValueError("Nur HTTP(S)-Ziele erlaubt")
    return value


def _send_whatsapp(config, destination, text):
    config = _required(config, ["access_token", "phone_number_id"])
    if not destination:
        raise ValueError("fehlendes Ziel")
    version = config.get("api_version", "v23.0")
    url = f"https://graph.facebook.com/{version}/" f"{config['phone_number_id']}/messages"
    if config.get("template_name"):
        payload = {
            "messaging_product": "whatsapp",
            "to": destination,
            "type": "template",
            "template": {
                "name": config["template_name"],
                "language": {"code": config.get("template_language", "de")},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": text}],
                    }
                ],
            },
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": destination,
            "type": "text",
            "text": {"body": text, "preview_url": False},
        }
    _http_json(
        "POST",
        url,
        payload,
        headers={"Authorization": f"Bearer {config['access_token']}"},
    )


def _send_telegram(config, destination, text):
    config = _required(config, ["bot_token"])
    if not destination:
        raise ValueError("fehlendes Ziel")
    url = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
    _http_json(
        "POST",
        url,
        {
            "chat_id": destination,
            "text": text,
            "disable_web_page_preview": True,
        },
    )


def _send_signal(config, destination, text):
    config = _required(config, ["api_url", "sender_number"])
    if not destination:
        raise ValueError("fehlendes Ziel")
    api_url = _config_url(config, "api_url")
    url = f"{api_url.rstrip('/')}/v2/send"
    headers = {}
    if config.get("authorization"):
        headers["Authorization"] = config["authorization"]
    _http_json(
        "POST",
        url,
        {
            "message": text,
            "number": config["sender_number"],
            "recipients": [destination],
        },
        headers=headers,
        insecure=bool(config.get("insecure_tls")),
    )


def _send_element(config, destination, text):
    config = _required(config, ["homeserver_url", "access_token"])
    if not destination:
        raise ValueError("fehlendes Ziel")
    room = urllib.parse.quote(destination, safe="")
    transaction_id = uuid.uuid4().hex
    homeserver_url = _config_url(config, "homeserver_url")
    url = (
        f"{homeserver_url.rstrip('/')}/_matrix/client/v3/rooms/"
        f"{room}/send/m.room.message/{transaction_id}"
    )
    _http_json(
        "PUT",
        url,
        {"msgtype": "m.text", "body": text},
        headers={"Authorization": f"Bearer {config['access_token']}"},
        insecure=bool(config.get("insecure_tls")),
    )


def _send_gotify(config, destination, text):
    config = _required(config, ["server_url", "app_token"])
    token = destination or config["app_token"]
    server_url = _config_url(config, "server_url")
    url = f"{server_url.rstrip('/')}/message?token={urllib.parse.quote(token)}"
    _http_json(
        "POST",
        url,
        {"title": "Club Zweisam", "message": text, "priority": 5},
        insecure=bool(config.get("insecure_tls")),
    )


SENDERS = {
    PROVIDER_WHATSAPP: _send_whatsapp,
    PROVIDER_TELEGRAM: _send_telegram,
    PROVIDER_SIGNAL: _send_signal,
    PROVIDER_ELEMENT: _send_element,
    PROVIDER_GOTIFY: _send_gotify,
}


def send_via_channel(channel, destination: str) -> bool:
    config = channel.get_config()
    sender = SENDERS.get(channel.provider)
    if sender is None:
        logger.warning("Unbekannter Benachrichtigungskanal %s", channel.pk)
        return False
    try:
        sender(config, destination, notification_text())
        return True
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
        except OSError:
            pass
        logger.warning(
            "Push-Zustellung fehlgeschlagen (Kanal %s, Provider %s): HTTP %s %s",
            channel.pk,
            channel.provider,
            exc.code,
            detail,
        )
        return False
    except Exception as exc:
        logger.warning(
            "Push-Zustellung fehlgeschlagen (Kanal %s, Provider %s): %s",
            channel.pk,
            channel.provider,
            exc.__class__.__name__,
        )
        return False


def dispatch_notification(notification) -> int:
    if notification.delivered_at is None or notification.clubroom_id is None:
        return 0
    sent = 0
    for channel in PersonalNotificationChannel.objects.filter(
        user_id=notification.user_id, is_enabled=True
    ):
        if not notification_allowed(
            notification.user, notification.clubroom, notification.event_type, channel.provider
        ):
            continue
        target = (channel.get_config().get("default_target") or "").strip()
        if target or channel.provider == PROVIDER_GOTIFY:
            if send_via_channel(channel, target):
                sent += 1
    channels = NotificationChannel.objects.filter(
        clubroom_id=notification.clubroom_id, is_enabled=True
    )
    for channel in channels:
        if not notification_allowed(
            notification.user, notification.clubroom, notification.event_type, channel.provider
        ):
            continue
        subscriptions = NotificationSubscription.objects.filter(
            channel=channel, user_id=notification.user_id, is_enabled=True
        )
        defaults = channel.get_config().get("default_target", "")
        targets = set()
        for subscription in subscriptions:
            target = (subscription.destination or "").strip() or (defaults or "").strip()
            if target:
                targets.add(target)
            elif channel.provider == PROVIDER_GOTIFY:
                targets.add("")
        for target in targets:
            if send_via_channel(channel, target):
                sent += 1
    return sent
