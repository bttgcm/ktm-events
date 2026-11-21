"""Adapter for community-suggested events submitted through the site's
"Suggest an event" Google Form.

Responses land in a Google Sheet. Unlike every other source, this one
isn't an organization's own listing - it's unmoderated public input -
so only rows with the "Approved" column checked (after a human has
looked at them) are turned into events. An unapproved or missing
"Approved" value just means the row is silently skipped, not an error.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Optional

import requests

from .base import Event, EventSourceAdapter

SHEET_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "16X9Y1E8t3zFr80P12UdFikBhxo0XoJeb6uuZX4YVAZA/export?format=csv"
)
FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSce8K4bl_wUzHlyVjsWnK4VhaU9buxhsTAwhGsgbxhKdEmLMQ/viewform"
)
REQUEST_TIMEOUT = 10
TRUTHY_VALUES = {"true", "yes", "1", "approved", "y"}


class SuggestedEventsAdapter(EventSourceAdapter):
    name = "Community Suggestions"

    def fetch_events(self) -> list[Event]:
        response = requests.get(SHEET_CSV_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return self._parse_csv(response.text)

    def _parse_csv(self, csv_text: str) -> list[Event]:
        events: list[Event] = []
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            event = self._parse_row(row)
            if event is not None:
                events.append(event)
        return events

    def _parse_row(self, row: dict) -> Optional[Event]:
        if (row.get("Approved") or "").strip().lower() not in TRUTHY_VALUES:
            return None

        title = (row.get("Event title") or "").strip()
        if not title:
            return None

        start = self._parse_datetime(row.get("Date") or "", row.get("Time") or "")
        if start is None:
            return None

        location = (row.get("location") or "").strip() or None
        link = (row.get("Link to event page") or "").strip() or FORM_URL
        description = (row.get("Event description") or "").strip() or None

        return Event(
            title=title,
            start=start,
            source_name=self.name,
            source_url=link,
            location=location,
            description=description,
        )

    @staticmethod
    def _parse_datetime(date_text: str, time_text: str) -> Optional[str]:
        date_text = date_text.strip()
        if not date_text:
            return None
        try:
            date_part = datetime.strptime(date_text, "%d/%m/%Y")
        except ValueError:
            return None

        hour = minute = 0
        time_text = time_text.strip()
        if time_text:
            try:
                time_part = datetime.strptime(time_text, "%H:%M:%S")
                hour, minute = time_part.hour, time_part.minute
            except ValueError:
                pass

        return date_part.replace(hour=hour, minute=minute).strftime("%Y-%m-%dT%H:%M:%S+05:45")
