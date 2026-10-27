"""Adapter for https://katajaam.com/events.

Note: unlike the other sources, Kata Jaam is a general Kathmandu event
discovery app (nightlife, food festivals, live music, etc.), not a
single cultural organization - it will pull in a broader mix of events.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import Event, EventSourceAdapter

LISTING_URL = "https://katajaam.com/events"
REQUEST_TIMEOUT = 10
RELATIVE_DAY_WORDS = {"today", "on now"}


class KataJaamAdapter(EventSourceAdapter):
    name = "Kata Jaam"

    def fetch_events(self) -> list[Event]:
        response = requests.get(LISTING_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return self._parse_listing(response.text, reference=datetime.now())

    def _parse_listing(self, html: str, reference: datetime) -> list[Event]:
        soup = BeautifulSoup(html, "html.parser")
        events: list[Event] = []
        for card in soup.select('a[href^="/events/"]'):
            event = self._parse_card(card, reference)
            if event is not None:
                events.append(event)
        return events

    def _parse_card(self, card, reference: datetime) -> Optional[Event]:
        href = card.get("href")
        if not href:
            return None
        title_el = card.select_one("h3")
        date_el = card.select_one("p")
        if title_el is None or date_el is None:
            return None

        start = self._parse_date(date_el.get_text(strip=True), reference)
        if start is None:
            return None

        venue_el = card.select_one("span.truncate")

        return Event(
            title=title_el.get_text(strip=True),
            start=start,
            source_name=self.name,
            source_url=urljoin(LISTING_URL, href),
            location=venue_el.get_text(strip=True) if venue_el else None,
        )

    @staticmethod
    def _parse_date(text: str, reference: datetime) -> Optional[str]:
        normalized = text.strip().lower()
        if normalized in RELATIVE_DAY_WORDS:
            date_part = reference.date()
        elif normalized == "tomorrow":
            date_part = (reference + timedelta(days=1)).date()
        else:
            match = re.search(r"([A-Za-z]+)\s+(\d{1,2})\s*$", text.strip())
            if not match:
                return None
            try:
                parsed = datetime.strptime(f"{match.group(1)} {match.group(2)}", "%b %d")
            except ValueError:
                return None
            candidate = parsed.replace(year=reference.year)
            # A date more than a week in the past is really next year's occurrence.
            if candidate.date() < (reference - timedelta(days=7)).date():
                candidate = candidate.replace(year=reference.year + 1)
            date_part = candidate.date()
        return f"{date_part.isoformat()}T00:00:00+05:45"
