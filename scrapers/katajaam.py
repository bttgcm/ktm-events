"""Adapter for https://katajaam.com/events/category/cultural.

Note: this still pulls from Kata Jaam, a general Kathmandu event
discovery app rather than a single cultural organization, but scoping
to the site's own "cultural" category keeps out the nightlife/food
events the unfiltered /events listing mixes in.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import Event, EventSourceAdapter

LISTING_URL = "https://katajaam.com/events/category/cultural"
REQUEST_TIMEOUT = 10
RELATIVE_DAY_WORDS = {"today": 0, "tomorrow": 1}

MONTH_DAY_PATTERN = re.compile(r"^([A-Za-z]{3,9})\.?\s+(\d{1,2})$")
TIME_PATTERN = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?$", re.IGNORECASE)


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
        title_el = card.select_one("span.font-bold")
        date_el = card.select_one("span.text-orange-ink")
        if title_el is None or date_el is None:
            return None

        start = self._parse_date(date_el.get_text(strip=True), reference)
        if start is None:
            return None

        location = None
        meta_el = card.select_one("span.text-ink-soft")
        if meta_el is not None:
            first_segment = meta_el.get_text(strip=True).split("·")[0].strip()
            location = first_segment or None

        return Event(
            title=title_el.get_text(strip=True),
            start=start,
            source_name=self.name,
            source_url=urljoin(LISTING_URL, href),
            location=location,
        )

    @classmethod
    def _parse_date(cls, text: str, reference: datetime) -> Optional[str]:
        # Segments are separated by "·" (middle dot), e.g.
        # "Today · 11 AM" or "New date·Dec 12 · 2 PM" - classify
        # each segment independently so an extra label like "New date"
        # is simply ignored rather than breaking the parse.
        date_part = None
        hour = minute = 0
        for segment in (s.strip() for s in text.split("·")):
            if not segment:
                continue
            if segment.lower() in RELATIVE_DAY_WORDS:
                offset = RELATIVE_DAY_WORDS[segment.lower()]
                date_part = (reference + timedelta(days=offset)).date()
                continue

            time_match = TIME_PATTERN.match(segment)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                meridiem = time_match.group(3).lower()
                if meridiem == "p" and hour != 12:
                    hour += 12
                elif meridiem == "a" and hour == 12:
                    hour = 0
                continue

            month_day_match = MONTH_DAY_PATTERN.match(segment)
            if month_day_match:
                parsed = cls._parse_month_day(month_day_match.group(1), month_day_match.group(2))
                if parsed is None:
                    continue
                candidate = parsed.replace(year=reference.year)
                # A date more than a week in the past is really next year's occurrence.
                if candidate.date() < (reference - timedelta(days=7)).date():
                    candidate = candidate.replace(year=reference.year + 1)
                date_part = candidate.date()

        if date_part is None:
            return None
        return f"{date_part.isoformat()}T{hour:02d}:{minute:02d}:00+05:45"

    @staticmethod
    def _parse_month_day(month_text: str, day_text: str) -> Optional[datetime]:
        for fmt in ("%b %d", "%B %d"):
            try:
                return datetime.strptime(f"{month_text} {day_text}", fmt)
            except ValueError:
                continue
        return None
