from datetime import UTC

from django.utils import timezone

from .models import KIND_TASK


def _escape(value: str) -> str:
    return (
        (value or "")
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _dt(value, all_day=False):
    if value is None:
        return ""
    value = value.astimezone(UTC)
    if all_day:
        return value.strftime("%Y%m%d")
    return value.strftime("%Y%m%dT%H%M%SZ")


def build_ics(entries, *, include_details=False, domain="club-zweisam.de"):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Club Zweisam//Kalender//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Club Zweisam – {domain}",
    ]
    now = _dt(timezone.now())
    for entry in entries:
        is_task = entry.kind == KIND_TASK
        lines += [
            "BEGIN:VTODO" if is_task else "BEGIN:VEVENT",
            f"UID:club-zweisam-{entry.pk}@{domain}",
            f"DTSTAMP:{now}",
            f"SUMMARY:{_escape(entry.title)}",
            (
                f"DTSTART;VALUE=DATE:{_dt(entry.start_at, True)}"
                if entry.all_day
                else f"DTSTART:{_dt(entry.start_at)}"
            ),
        ]
        if entry.end_at:
            lines.append(
                f"DUE;VALUE=DATE:{_dt(entry.end_at, True)}"
                if is_task and entry.all_day
                else (
                    f"DUE:{_dt(entry.end_at)}"
                    if is_task
                    else (
                        f"DTEND;VALUE=DATE:{_dt(entry.end_at, True)}"
                        if entry.all_day
                        else f"DTEND:{_dt(entry.end_at)}"
                    )
                )
            )
        if include_details and entry.description:
            lines.append(f"DESCRIPTION:{_escape(entry.description)}")
        if is_task:
            lines.append(f"STATUS:{'COMPLETED' if entry.is_done else 'NEEDS-ACTION'}")
        lines += ["END:VTODO" if is_task else "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
