"""Adapter for https://kathmanduinstitute.org.np/monthly-events/.

The listing page is a retrospective photo gallery of past monthly
talks, grouped by month - most months are just a poster image with no
link to a detail page, so there's nothing to extract there. Only
months that do link to a detail page are followed; all real fields
(date, venue, speaker) come from that detail page, the same
listing-gives-urls-only/detail-has-the-data split as the Mandala
Theatre adapter.
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import Event, EventSourceAdapter

LISTING_URL = "https://kathmanduinstitute.org.np/monthly-events/"
REQUEST_TIMEOUT = 10
DETAIL_FETCH_DELAY_SECONDS = 0.5

FIELD_PATTERN = re.compile(r"^(?P<label>[A-Za-z ]+)\s*:\s*(?P<value>.+)$")
WEEKDAY_PREFIX_PATTERN = re.compile(r"^[A-Za-z]+,\s*")


class KathmanduInstituteAdapter(EventSourceAdapter):
    name = "Kathmandu Institute"

    def fetch_events(self) -> list[Event]:
        response = requests.get(LISTING_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        urls = self._extract_event_urls(response.text)

        events: list[Event] = []
        for url in urls:
            event = self._fetch_event_detail(url)
            if event is not None:
                events.append(event)
        return events

    @staticmethod
    def _extract_event_urls(html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        listing_url_normalized = LISTING_URL.rstrip("/")
        urls: list[str] = []
        seen: set[str] = set()
        for a in soup.select(f'a[href^="{LISTING_URL}"]'):
            href = a.get("href")
            if not href:
                continue
            url = urljoin(LISTING_URL, href)
            if url.rstrip("/") == listing_url_normalized or url in seen:
                continue
            seen.add(url)
            urls.append(url)
        return urls

    def _fetch_event_detail(self, url: str) -> Optional[Event]:
        try:
            time.sleep(DETAIL_FETCH_DELAY_SECONDS)
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException:
            return None
        return self._parse_detail(url, response.text)

    def _parse_detail(self, url: str, html: str) -> Optional[Event]:
        soup = BeautifulSoup(html, "html.parser")

        title_el = soup.select_one("h2.elementor-heading-title")
        if title_el is None:
            return None

        fields = self._extract_fields(soup)
        date_text = fields.get("date")
        if not date_text:
            return None
        start = self._parse_date(date_text)
        if start is None:
            return None

        speaker = fields.get("speaker")

        return Event(
            title=title_el.get_text(strip=True),
            start=start,
            source_name=self.name,
            source_url=url,
            location=fields.get("venue"),
            description=f"Speaker: {speaker}" if speaker else None,
        )

    @staticmethod
    def _extract_fields(soup) -> dict[str, str]:
        fields: dict[str, str] = {}
        for p in soup.select(".elementor-widget-text-editor p"):
            match = FIELD_PATTERN.match(p.get_text(" ", strip=True))
            if match:
                fields[match.group("label").strip().lower()] = match.group("value").strip()
        return fields

    @staticmethod
    def _parse_date(text: str) -> Optional[str]:
        cleaned = WEEKDAY_PREFIX_PATTERN.sub("", text).strip()
        try:
            dt = datetime.strptime(cleaned, "%B %d, %Y")
        except ValueError:
            return None
        return dt.strftime("%Y-%m-%dT00:00:00+05:45")
