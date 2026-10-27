"""Adapter for https://nepalartcouncil.org.np/category/current-exhibition/.

Exhibition dates aren't a labeled field here - they're free-form prose
inside the post excerpt (e.g. "Date: 17th September - 10th October,
2026"), so this is the most regex-heavy, most fragile adapter of the
bunch: a wording change on the source site is more likely to break it
than the other sources' more structured markup.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import Event, EventSourceAdapter

LISTING_URL = "https://nepalartcouncil.org.np/category/current-exhibition/"
REQUEST_TIMEOUT = 10

ORDINAL_SUFFIX_PATTERN = re.compile(r"(\d{1,2})(st|nd|rd|th)", re.IGNORECASE)
DATE_LINE_PATTERN = re.compile(r"Date:\s*(.+)", re.IGNORECASE)
RANGE_SPLIT_PATTERN = re.compile(r"[–—-]")


class NepalArtCouncilAdapter(EventSourceAdapter):
    name = "Nepal Art Council"

    def fetch_events(self) -> list[Event]:
        response = requests.get(LISTING_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return self._parse_listing(response.text)

    def _parse_listing(self, html: str) -> list[Event]:
        soup = BeautifulSoup(html, "html.parser")
        events: list[Event] = []
        for article in soup.select("article"):
            event = self._parse_article(article)
            if event is not None:
                events.append(event)
        return events

    def _parse_article(self, article) -> Optional[Event]:
        title_el = article.select_one(".entry-title a")
        if title_el is None or not title_el.get("href"):
            return None

        excerpt_el = article.select_one(".ast-excerpt-container")
        if excerpt_el is None:
            return None

        date_match = DATE_LINE_PATTERN.search(excerpt_el.get_text("\n"))
        if not date_match:
            return None
        start, end = self._parse_date_range(date_match.group(1))
        if start is None:
            return None

        return Event(
            title=title_el.get_text(strip=True),
            start=start,
            end=end,
            source_name=self.name,
            source_url=urljoin(LISTING_URL, title_el["href"]),
            description=excerpt_el.get_text(" ", strip=True),
        )

    @classmethod
    def _parse_date_range(cls, text: str) -> tuple[Optional[str], Optional[str]]:
        text = text.split("\n")[0].strip()
        parts = RANGE_SPLIT_PATTERN.split(text, maxsplit=1)
        if len(parts) == 2:
            start_text, end_text = (p.strip() for p in parts)
        else:
            start_text = end_text = text

        end_dt = cls._parse_single_date(end_text)
        if end_dt is None:
            return None, None
        start_dt = cls._parse_single_date(start_text, fallback_year=end_dt.year)
        if start_dt is None:
            return None, None

        start_iso = start_dt.strftime("%Y-%m-%dT00:00:00+05:45")
        end_iso = None if start_dt == end_dt else end_dt.strftime("%Y-%m-%dT00:00:00+05:45")
        return start_iso, end_iso

    @staticmethod
    def _parse_single_date(text: str, fallback_year: Optional[int] = None) -> Optional[datetime]:
        cleaned = ORDINAL_SUFFIX_PATTERN.sub(r"\1", text).replace(",", "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        for fmt in ("%d %B %Y", "%d %B"):
            try:
                dt = datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
            if "%Y" not in fmt and fallback_year is not None:
                dt = dt.replace(year=fallback_year)
            return dt
        return None
