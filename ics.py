"""Builds an RFC 5545 iCalendar feed from Event objects, so the whole
event list can be subscribed to from a phone/desktop calendar app."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from scrapers.base import Event

DEFAULT_DURATION = timedelta(hours=1)
PRODID = "-//Kathmandu Cultural Events//EN"


def _to_ics_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _event_to_vevent_lines(event: Event, now: datetime) -> list[str]:
    start = datetime.fromisoformat(event.start)
    end = datetime.fromisoformat(event.end) if event.end else start + DEFAULT_DURATION

    description_parts = []
    if event.description:
        description_parts.append(event.description)
    description_parts.append(event.source_url)

    lines = [
        "BEGIN:VEVENT",
        f"UID:{event.id}@ktm-events",
        f"DTSTAMP:{_to_ics_utc(now)}",
        f"DTSTART:{_to_ics_utc(start)}",
        f"DTEND:{_to_ics_utc(end)}",
        f"SUMMARY:{_escape(event.title)}",
        f"DESCRIPTION:{_escape(chr(10).join(description_parts))}",
        f"URL:{event.source_url}",
    ]
    if event.location:
        lines.append(f"LOCATION:{_escape(event.location)}")
    lines.append("END:VEVENT")
    return lines


def build_calendar(events: Iterable[Event]) -> str:
    """Return a full VCALENDAR document containing one VEVENT per event."""
    now = datetime.now(timezone.utc)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:Kathmandu Cultural Events",
    ]
    for event in events:
        lines.extend(_event_to_vevent_lines(event, now))
    lines.append("END:VCALENDAR")
    # RFC 5545 requires CRLF line endings; write as bytes later to avoid
    # the platform text-mode newline translation mangling them.
    return "\r\n".join(lines) + "\r\n"
