from pathlib import Path

from scrapers.nepal_art_council import NepalArtCouncilAdapter

FIXTURE_HTML = (
    Path(__file__).parent / "fixtures" / "nepal_art_council_current_exhibition.html"
).read_text(encoding="utf-8")


def test_parse_listing_extracts_exhibition_with_date_range():
    adapter = NepalArtCouncilAdapter()
    events = adapter._parse_listing(FIXTURE_HTML)

    assert len(events) == 1
    event = events[0]
    assert event.title == "Deities of Nepal III"
    assert event.start == "2026-09-17T00:00:00+05:45"
    assert event.end == "2026-10-10T00:00:00+05:45"
    assert event.source_url == "https://nepalartcouncil.org.np/deities-of-nepal-iii-2/"


def test_parse_date_range_handles_ordinal_suffixes_and_shared_year():
    start, end = NepalArtCouncilAdapter._parse_date_range("17th September – 10th October, 2026")
    assert start == "2026-09-17T00:00:00+05:45"
    assert end == "2026-10-10T00:00:00+05:45"


def test_parse_date_range_handles_single_date_without_range():
    start, end = NepalArtCouncilAdapter._parse_date_range("5th October, 2026")
    assert start == "2026-10-05T00:00:00+05:45"
    assert end is None


def test_parse_date_range_returns_none_for_unparseable_text():
    start, end = NepalArtCouncilAdapter._parse_date_range("sometime next month")
    assert start is None
    assert end is None
