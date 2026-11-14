import json
import urllib.error
import urllib.request


class TelegramError(Exception):
    pass


def _call(token: str, method: str, payload: dict | None = None) -> dict:
    if not token:
        raise TelegramError("Bot-Token fehlt.")
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # nosec B310
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            description = body.get("description") or "Telegram-API-Fehler"
        except (ValueError, UnicodeDecodeError):
            description = "Telegram-API-Fehler"
        raise TelegramError(description) from None
    except (OSError, ValueError) as exc:
        raise TelegramError(f"Telegram nicht erreichbar: {exc.__class__.__name__}") from None


def discover_chats(token: str) -> list[dict]:
    result = _call(
        token,
        "getUpdates",
        {"timeout": 0, "allowed_updates": ["message", "my_chat_member", "channel_post"]},
    )
    chats: dict[int, dict] = {}
    for update in result.get("result", []):
        for key in ("message", "channel_post", "my_chat_member"):
            chat = (update.get(key) or {}).get("chat")
            if not chat:
                continue
            chat_id = chat.get("id")
            if chat_id is None:
                continue
            chats[chat_id] = {
                "id": chat_id,
                "type": chat.get("type", ""),
                "title": chat.get("title")
                or chat.get("username")
                or " ".join(
                    part for part in (chat.get("first_name"), chat.get("last_name")) if part
                )
                or str(chat_id),
                "username": chat.get("username", ""),
            }
    return sorted(chats.values(), key=lambda chat: (chat["type"], chat["title"]))
