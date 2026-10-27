from datetime import datetime
from pathlib import Path

from scrapers.katajaam import KataJaamAdapter

FIXTURE_HTML = (Path(__file__).parent / "fixtures" / "katajaam_events.html").read_text(encoding="utf-8")

REFERENCE = datetime(2026, 9, 28, 12, 0, 0)


def test_parse_listing_extracts_events_with_titles_dates_and_venues():
    adapter = KataJaamAdapter()
    events = adapter._parse_listing(FIXTURE_HTML, reference=REFERENCE)

    assert len(events) > 0
    assert all(e.source_url.startswith("https://katajaam.com/events/") for e in events)
    assert any(e.location for e in events)

    gen_v = next(e for e in events if "Gen V" in e.title)
    assert gen_v.start == "2026-09-26T00:00:00+05:45"
    assert gen_v.location == "The Concept, Butwal"


def test_parse_date_handles_relative_and_absolute_forms():
    parse = KataJaamAdapter._parse_date
    assert parse("Today", REFERENCE) == "2026-09-28T00:00:00+05:45"
    assert parse("Tomorrow", REFERENCE) == "2026-09-29T00:00:00+05:45"
    assert parse("On now", REFERENCE) == "2026-09-28T00:00:00+05:45"
    assert parse("Wednesday, Sep 30", REFERENCE) == "2026-09-30T00:00:00+05:45"


def test_parse_date_rolls_over_to_next_year_when_far_in_the_past():
    # Reference is late Sept 2026; "Jan 5" should mean Jan 5, 2027.
    assert KataJaamAdapter._parse_date("Monday, Jan 5", REFERENCE) == "2027-01-05T00:00:00+05:45"


def test_parse_date_returns_none_for_unrecognized_text():
    assert KataJaamAdapter._parse_date("Free to list", REFERENCE) is None
