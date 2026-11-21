from datetime import datetime
from pathlib import Path

from scrapers.katajaam import KataJaamAdapter

FIXTURE_HTML = (Path(__file__).parent / "fixtures" / "katajaam_events.html").read_text(encoding="utf-8")

REFERENCE = datetime(2026, 11, 21, 12, 0, 0)


def test_parse_listing_extracts_events_and_skips_category_nav_links():
    adapter = KataJaamAdapter()
    events = adapter._parse_listing(FIXTURE_HTML, reference=REFERENCE)

    assert len(events) == 4
    assert all(e.source_url.startswith("https://katajaam.com/events/") for e in events)
    assert all("/category/" not in e.source_url for e in events)

    walk = next(e for e in events if "Banepa Heritage Walk" in e.title)
    assert walk.start == "2026-11-21T11:00:00+05:45"
    assert walk.location == "Banepa"


def test_parse_date_handles_today_and_tomorrow_with_time():
    parse = KataJaamAdapter._parse_date
    assert parse("Today · 11 AM", REFERENCE) == "2026-11-21T11:00:00+05:45"
    assert parse("Tomorrow · 4 PM", REFERENCE) == "2026-11-22T16:00:00+05:45"


def test_parse_date_handles_month_day_without_time():
    assert KataJaamAdapter._parse_date("Dec 4", REFERENCE) == "2026-12-04T00:00:00+05:45"


def test_parse_date_ignores_extra_label_segments():
    # "New date·Dec 12 · 2 PM" - the "New date" label should just be skipped.
    assert KataJaamAdapter._parse_date("New date·Dec 12 · 2 PM", REFERENCE) == "2026-12-12T14:00:00+05:45"


def test_parse_date_rolls_over_to_next_year_when_far_in_the_past():
    assert KataJaamAdapter._parse_date("Jan 5", REFERENCE) == "2027-01-05T00:00:00+05:45"


def test_parse_date_returns_none_for_unrecognized_text():
    assert KataJaamAdapter._parse_date("Free to list", REFERENCE) is None
