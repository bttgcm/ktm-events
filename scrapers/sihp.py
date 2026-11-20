"""Adapter for https://sihp.edu.np/category/news/.

This is a general news feed, not a dedicated events page - most posts
are announcements (partnerships, admissions, LoAs) with no event date
to extract. Only posts whose excerpt embeds a "Date:" field (the
pattern SIHP uses when announcing a talk/lecture) are treated as
events; everything else is skipped.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import Event, EventSourceAdapter

LISTING_URL = "https://sihp.edu.np/category/news/"
REQUEST_TIMEOUT = 10

ORDINAL_SUFFIX_PATTERN = re.compile(r"(\d{1,2})(st|nd|rd|th)", re.IGNORECASE)
PARENTHETICAL_PATTERN = re.compile(r"\([^)]*\)")
DATE_FIELD_PATTERN = re.compile(r"Date:\s*(.+?)(?=Time:|Venue:|$)", re.IGNORECASE)
TIME_FIELD_PATTERN = re.compile(r"Time:\s*(.+?)(?=Venue:|$)", re.IGNORECASE)
VENUE_FIELD_PATTERN = re.compile(r"Venue:\s*(.+?)(?:…|$)", re.IGNORECASE)
TIME_RANGE_PATTERN = re.compile(
    r"(?P<h1>\d{1,2})(?::(?P<m1>\d{2}))?\s*(?P<ap1>[ap])\.?m\.?"
    r"(?:\s*[–—-]\s*(?P<h2>\d{1,2})(?::(?P<m2>\d{2}))?\s*(?P<ap2>[ap])\.?m\.?)?",
    re.IGNORECASE,
)


class SihpAdapter(EventSourceAdapter):
    name = "SIHP"

    def fetch_events(self) -> list[Event]:
        response = requests.get(LISTING_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return self._parse_listing(response.text)

    def _parse_listing(self, html: str) -> list[Event]:
        soup = BeautifulSoup(html, "html.parser")
        events: list[Event] = []
        for post in soup.select("li.wp-block-post"):
            event = self._parse_post(post)
            if event is not None:
                events.append(event)
        return events

    def _parse_post(self, post) -> Optional[Event]:
        title_link = post.select_one(".wp-block-post-title a")
        if title_link is None or not title_link.get("href"):
            return None

        excerpt_el = post.select_one(".wp-block-post-excerpt__excerpt")
        if excerpt_el is None:
            return None
        excerpt_text = excerpt_el.get_text(" ", strip=True)

        date_match = DATE_FIELD_PATTERN.search(excerpt_text)
        if not date_match:
            return None
        start, end = self._parse_date_and_time(date_match.group(1), excerpt_text)
        if start is None:
            return None

        venue_match = VENUE_FIELD_PATTERN.search(excerpt_text)
        location = venue_match.group(1).strip() if venue_match else None

        description = re.sub(r"\s+", " ", excerpt_text[: date_match.start()]).strip() or None

        categories = [
            c[len("category-") :].replace("-", " ").title()
            for c in post.get("class", [])
            if c.startswith("category-") and c != "category-news"
        ]

        return Event(
            title=title_link.get_text(strip=True),
            start=start,
            end=end,
            source_name=self.name,
            source_url=urljoin(LISTING_URL, title_link["href"]),
            description=description,
            location=location,
            categories=categories,
        )

    @classmethod
    def _parse_date_and_time(
        cls, date_text: str, excerpt_text: str
    ) -> tuple[Optional[str], Optional[str]]:
        date_only = cls._parse_date_only(date_text)
        if date_only is None:
            return None, None

        time_match = TIME_FIELD_PATTERN.search(excerpt_text)
        range_match = TIME_RANGE_PATTERN.search(time_match.group(1)) if time_match else None
        if range_match is None:
            return date_only.strftime("%Y-%m-%dT00:00:00+05:45"), None

        start_dt = cls._combine(date_only, range_match, "1")
        end_dt = cls._combine(date_only, range_match, "2") if range_match.group("h2") else None
        start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%S+05:45")
        end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%S+05:45") if end_dt else None
        return start_iso, end_iso

    @staticmethod
    def _combine(date_only: datetime, match: re.Match, suffix: str) -> datetime:
        hour = int(match.group(f"h{suffix}"))
        minute = int(match.group(f"m{suffix}") or 0)
        meridiem = match.group(f"ap{suffix}").lower()
        if meridiem == "p" and hour != 12:
            hour += 12
        elif meridiem == "a" and hour == 12:
            hour = 0
        return date_only.replace(hour=hour, minute=minute)

    @staticmethod
    def _parse_date_only(text: str) -> Optional[datetime]:
        cleaned = PARENTHETICAL_PATTERN.sub("", text)
        cleaned = ORDINAL_SUFFIX_PATTERN.sub(r"\1", cleaned).replace(",", "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        try:
            return datetime.strptime(cleaned, "%d %B %Y")
        except ValueError:
            return None
