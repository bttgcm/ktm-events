"""Adapter for https://taragaonnext.com/whats-on/."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import Event, EventSourceAdapter

LISTING_URL = "https://taragaonnext.com/whats-on/"
REQUEST_TIMEOUT = 10

# e.g. "September 18, 2026 | 4:00 p.m." or "September 13, 2026 | 7 a.m."
DATE_PATTERN = re.compile(
    r"(?P<month_day_year>[A-Za-z]+ \d{1,2}, \d{4})\s*\|\s*"
    r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<meridiem>[ap])\.?m\.?",
    re.IGNORECASE,
)


class TaragaonNextAdapter(EventSourceAdapter):
    name = "Taragaon Next"

    def fetch_events(self) -> list[Event]:
        response = requests.get(LISTING_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return self._parse_listing(response.text)

    def _parse_listing(self, html: str) -> list[Event]:
        soup = BeautifulSoup(html, "html.parser")
        events: list[Event] = []
        seen_urls: set[str] = set()
        for item in soup.select(".event-item"):
            event = self._parse_item(item)
            if event is None or event.source_url in seen_urls:
                continue
            seen_urls.add(event.source_url)
            events.append(event)
        return events

    def _parse_item(self, item) -> Optional[Event]:
        title_el = item.select_one(".event-title")
        link_el = item.select_one("a.event-link")
        date_el = item.select_one(".event-date")
        if title_el is None or link_el is None or date_el is None or not link_el.get("href"):
            return None

        start = self._parse_date(date_el.get_text(strip=True))
        if start is None:
            return None

        categories = [
            li.get_text(strip=True) for li in item.select(".event-category li") if li.get_text(strip=True)
        ]

        return Event(
            title=title_el.get_text(strip=True),
            start=start,
            source_name=self.name,
            source_url=urljoin(LISTING_URL, link_el["href"]),
            categories=categories,
        )

    @staticmethod
    def _parse_date(text: str) -> Optional[str]:
        match = DATE_PATTERN.search(text)
        if not match:
            return None
        hour = int(match.group("hour"))
        minute = int(match.group("minute") or 0)
        meridiem = match.group("meridiem").lower()
        if meridiem == "p" and hour != 12:
            hour += 12
        elif meridiem == "a" and hour == 12:
            hour = 0
        try:
            date_part = datetime.strptime(match.group("month_day_year"), "%B %d, %Y")
        except ValueError:
            return None
        dt = date_part.replace(hour=hour, minute=minute)
        return dt.strftime("%Y-%m-%dT%H:%M:%S+05:45")
