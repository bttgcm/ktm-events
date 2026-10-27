"""Adapter for https://www.mandalatheatre.com/events/.

The archive page only gives us event detail-page URLs (the teaser
markup is too entangled with generic page-builder wrapper divs to
extract reliably) - all real fields come from each detail page.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import Event, EventSourceAdapter

LISTING_URL = "https://www.mandalatheatre.com/events/"
REQUEST_TIMEOUT = 10
DETAIL_FETCH_DELAY_SECONDS = 0.5

STARTS_ON_PATTERN = re.compile(r"Starts on\s*:\s*([^\n]+)", re.IGNORECASE)
ENDS_ON_PATTERN = re.compile(r"Ends on\s*:\s*([^\n]+)", re.IGNORECASE)
EVENT_TYPE_PATTERN = re.compile(r"Event Type\s*:\s*([^\n]+)", re.IGNORECASE)


class MandalaTheatreAdapter(EventSourceAdapter):
    name = "Mandala Theatre"

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
        for a in soup.select("a.jet-listing-dynamic-link__link"):
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
        title = self._extract_title(html)
        if title is None:
            return None

        text = BeautifulSoup(html, "html.parser").get_text("\n")
        starts_match = STARTS_ON_PATTERN.search(text)
        if starts_match is None:
            return None
        start = self._parse_date_only(starts_match.group(1).strip())
        if start is None:
            return None

        ends_match = ENDS_ON_PATTERN.search(text)
        end = self._parse_date_only(ends_match.group(1).strip()) if ends_match else None

        categories = []
        type_match = EVENT_TYPE_PATTERN.search(text)
        if type_match:
            categories.append(type_match.group(1).strip())

        return Event(
            title=title,
            start=start,
            end=end,
            source_name=self.name,
            source_url=url,
            categories=categories,
        )

    @staticmethod
    def _extract_title(html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.select('script[type="application/ld+json"]'):
            if not script.string:
                continue
            try:
                data = json.loads(script.string, strict=False)
            except json.JSONDecodeError:
                continue
            for graph_item in data.get("@graph", [data]):
                if graph_item.get("@type") != "BreadcrumbList":
                    continue
                items = graph_item.get("itemListElement", [])
                if items:
                    name = items[-1].get("item", {}).get("name")
                    if name:
                        return name
        og_title = soup.select_one('meta[property="og:title"]')
        if og_title and og_title.get("content"):
            return og_title["content"]
        return None

    @staticmethod
    def _parse_date_only(text: str) -> Optional[str]:
        try:
            dt = datetime.strptime(text, "%B %d, %Y")
        except ValueError:
            return None
        return dt.strftime("%Y-%m-%dT00:00:00+05:45")
