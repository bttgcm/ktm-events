"""Adapter for https://martinchautari.org.np/events."""

from __future__ import annotations

import json
import time
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import Event, EventSourceAdapter

LISTING_URL = "https://martinchautari.org.np/events"
PLACEHOLDER_IMAGE = "img-not-found.png"
REQUEST_TIMEOUT = 10
DETAIL_FETCH_DELAY_SECONDS = 0.5


class MartinChautariAdapter(EventSourceAdapter):
    name = "Martin Chautari"

    def fetch_events(self) -> list[Event]:
        response = requests.get(LISTING_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        events = self._parse_listing(response.text)
        for event in events:
            self._enrich_from_detail_page(event)
        return events

    def _parse_listing(self, html: str) -> list[Event]:
        soup = BeautifulSoup(html, "html.parser")
        events: list[Event] = []
        for card in soup.select(".Events .card"):
            event = self._parse_card(card)
            if event is not None:
                events.append(event)
        return events

    def _parse_card(self, card) -> Optional[Event]:
        title_link = card.select_one("h2.card-title a")
        if title_link is None or not title_link.get("href"):
            return None
        title = title_link.get_text(strip=True)
        source_url = urljoin(LISTING_URL, title_link["href"])

        categories = [a.get_text(strip=True) for a in card.select("span.text-warning a")]

        time_tags = card.select("span.text-muted time")
        if not time_tags:
            return None
        start = time_tags[0].get("datetime")
        end = time_tags[1].get("datetime") if len(time_tags) > 1 else None
        if not start:
            return None

        description = None
        speaker_link = card.select_one("div.pb-2 a")
        if speaker_link:
            description = f"Speaker: {speaker_link.get_text(strip=True)}"

        return Event(
            title=title,
            start=start,
            end=end,
            source_name=self.name,
            source_url=source_url,
            categories=categories,
            description=description,
        )

    def _enrich_from_detail_page(self, event: Event) -> None:
        try:
            time.sleep(DETAIL_FETCH_DELAY_SECONDS)
            response = requests.get(event.source_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException:
            return
        self._apply_detail_data(event, self._extract_ld_json(response.text))

    @staticmethod
    def _apply_detail_data(event: Event, data: dict) -> None:
        description = data.get("description")
        if description:
            event.description = description.strip()

        images = data.get("image")
        if isinstance(images, list) and images:
            images = images[0]
        if isinstance(images, str) and images and PLACEHOLDER_IMAGE not in images:
            event.image = images

        location = data.get("location")
        if isinstance(location, dict):
            address = (location.get("address") or "").strip()
            if address:
                event.location = address

    @staticmethod
    def _extract_ld_json(html: str) -> dict:
        """Merge every JSON-LD block on a detail page into one dict.

        Some blocks on this site embed literal newlines inside string
        values (e.g. the "description" field), which is invalid strict
        JSON - strict=False tells json.loads to tolerate that instead of
        raising.
        """
        soup = BeautifulSoup(html, "html.parser")
        merged: dict = {}
        for script in soup.select('script[type="application/ld+json"]'):
            if not script.string:
                continue
            try:
                data = json.loads(script.string, strict=False)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                merged.update(data)
        return merged
