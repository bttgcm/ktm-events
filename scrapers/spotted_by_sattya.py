"""Adapter for the "Spotted by Sattya" Substack newsletter.

Unlike the other sources, this isn't a per-event listing - it's a
weekly digest. Each RSS item covers one week and its content:encoded
body is a series of "<h3>weekday - month day</h3>" day headings, each
followed by a single "<p>" containing one or more "<strong>"-led event
blocks (time/category/title, then a description and an "<em>" venue
line with an optional link). We parse the RSS feed directly rather
than the public archive page - no HTML fetch of the site itself needed.

This is the most implementation-heavy adapter of the set: it depends
on a prose convention the newsletter author could change at any time,
more so than the other sources' page markup.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

from .base import Event, EventSourceAdapter

FEED_URL = "https://spottedbysattya.substack.com/feed"
REQUEST_TIMEOUT = 10
MAX_POSTS = 6  # a handful of recent weekly digests is plenty

# Substack's CDN 403s requests with no User-Agent (the default
# "python-requests/x.y"), which is what GitHub Actions runners send -
# a real browser UA gets through from both local machines and CI.
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )
}

CONTENT_ENCODED_TAG = "{http://purl.org/rss/1.0/modules/content/}encoded"

# "friday - september 25" (no year given)
DAY_HEADING_PATTERN = re.compile(
    r"^[a-z]+\s*[–—-]\s*([a-z]+)\s+(\d{1,2})\s*$", re.IGNORECASE
)
# "fri 4:30pm: FILM - knowledge-making beyond text"
EVENT_HEADER_PATTERN = re.compile(r"^\S+\s+([\d:apm]+)\s*:\s*([A-Z]+)\s*[–—-]\s*(.+)$")
TIME_PATTERN = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", re.IGNORECASE)


class SpottedBySattyaAdapter(EventSourceAdapter):
    name = "Spotted by Sattya"

    def fetch_events(self) -> list[Event]:
        response = requests.get(FEED_URL, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return self._parse_feed(response.content)

    def _parse_feed(self, xml_bytes: bytes) -> list[Event]:
        root = ElementTree.fromstring(xml_bytes)
        events: list[Event] = []
        for item in root.findall("./channel/item")[:MAX_POSTS]:
            events.extend(self._parse_item(item))
        return events

    def _parse_item(self, item) -> list[Event]:
        content_el = item.find(CONTENT_ENCODED_TAG)
        link_el = item.find("link")
        if content_el is None or content_el.text is None or link_el is None or not link_el.text:
            return []

        pub_date_el = item.find("pubDate")
        reference_date = datetime.now(timezone.utc)
        if pub_date_el is not None and pub_date_el.text:
            try:
                reference_date = parsedate_to_datetime(pub_date_el.text)
            except (TypeError, ValueError):
                pass

        return self._parse_content(content_el.text, link_el.text.strip(), reference_date)

    def _parse_content(self, html: str, post_url: str, reference_date: datetime) -> list[Event]:
        soup = BeautifulSoup(html, "html.parser")
        events: list[Event] = []
        for heading in soup.find_all("h3"):
            day = self._parse_day_heading(heading.get_text(strip=True), reference_date)
            if day is None:
                continue
            paragraph = heading.find_next_sibling("p")
            if paragraph is None:
                continue
            events.extend(self._parse_day_paragraph(paragraph, day, post_url))
        return events

    @staticmethod
    def _parse_day_heading(text: str, reference_date: datetime) -> Optional[datetime]:
        match = DAY_HEADING_PATTERN.match(text.strip())
        if not match:
            return None
        month_name, day_number = match.groups()
        try:
            parsed = datetime.strptime(f"{month_name} {day_number}", "%B %d")
        except ValueError:
            return None

        naive_reference = reference_date.replace(tzinfo=None)
        candidate = parsed.replace(year=naive_reference.year)
        # A digest only ever covers the week around its publish date - if
        # the same-year guess is way off, the heading is really in the
        # other year (e.g. a January issue covering late December).
        if abs((candidate - naive_reference).days) > 30:
            candidate = candidate.replace(
                year=naive_reference.year + (1 if candidate < naive_reference else -1)
            )
        return candidate

    def _parse_day_paragraph(self, paragraph, day: datetime, post_url: str) -> list[Event]:
        events: list[Event] = []
        for index, strong in enumerate(paragraph.find_all("strong")):
            event = self._parse_event_block(strong, day, post_url, index)
            if event is not None:
                events.append(event)
        return events

    def _parse_event_block(self, strong, day: datetime, post_url: str, index: int) -> Optional[Event]:
        header_match = EVENT_HEADER_PATTERN.match(strong.get_text(strip=True))
        if not header_match:
            return None
        time_text, category, title = header_match.groups()

        description_parts: list[str] = []
        link: Optional[str] = None
        node = strong.next_sibling
        while node is not None and getattr(node, "name", None) != "strong":
            if getattr(node, "name", None) == "em":
                em_link = node.find("a")
                if em_link is not None and em_link.get("href") and link is None:
                    link = em_link["href"]
                text = node.get_text(" ", strip=True)
                if text and text != "»":
                    description_parts.append(text)
            elif isinstance(node, str):
                text = node.strip()
                if text:
                    description_parts.append(text)
            node = node.next_sibling

        # The same Instagram link (or, lacking one, the same post URL) can
        # legitimately recur across different days/weeks for a recurring
        # event - append day+index so each occurrence still gets a
        # distinct id rather than colliding in the pipeline's dedupe step.
        unique_suffix = f"{day.date().isoformat()}-{index}"
        source_url = f"{link}#{unique_suffix}" if link else f"{post_url}#{unique_suffix}"

        return Event(
            title=title.strip(),
            start=self._combine_date_and_time(day, time_text),
            source_name=self.name,
            source_url=source_url,
            description=" ".join(description_parts).strip() or None,
            categories=[category.strip().title()],
        )

    @staticmethod
    def _combine_date_and_time(day: datetime, time_text: str) -> str:
        match = TIME_PATTERN.match(time_text)
        if not match:
            return day.strftime("%Y-%m-%dT00:00:00+05:45")
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = match.group(3).lower()
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        return day.replace(hour=hour, minute=minute, second=0).strftime("%Y-%m-%dT%H:%M:%S+05:45")
