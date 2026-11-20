from pathlib import Path

from scrapers.sihp import SihpAdapter

FIXTURE_HTML = (Path(__file__).parent / "fixtures" / "sihp_news.html").read_text(encoding="utf-8")


def test_parse_listing_only_returns_posts_with_a_date_field():
    adapter = SihpAdapter()
    events = adapter._parse_listing(FIXTURE_HTML)

    assert len(events) == 1
    event = events[0]
    assert event.title == "Lecture Series: Looking to a Post-Combustion Future"
    assert event.start == "2026-01-16T15:45:00+05:45"
    assert event.end == "2026-01-16T17:00:00+05:45"
    assert event.location == "YalaMaya Kendra, Patan"
    assert event.source_url == "https://sihp.edu.np/lecture-series-looking-to-a-post-combustion-future/"
    assert "Date:" not in (event.description or "")
    assert "Forms" in event.categories
    assert "News" not in event.categories


def test_parse_date_and_time_handles_weekday_parenthetical_and_time_range():
    start, end = SihpAdapter._parse_date_and_time(
        "16 January 2026 (Friday)",
        "Date: 16 January 2026 (Friday)Time: 3:45 pm–5:00 pmVenue: Somewhere",
    )
    assert start == "2026-01-16T15:45:00+05:45"
    assert end == "2026-01-16T17:00:00+05:45"


def test_parse_date_and_time_without_time_field_defaults_to_midnight():
    start, end = SihpAdapter._parse_date_and_time("1 March 2026", "Date: 1 March 2026")
    assert start == "2026-03-01T00:00:00+05:45"
    assert end is None


def test_parse_date_and_time_returns_none_for_unparseable_date():
    start, end = SihpAdapter._parse_date_and_time("whenever", "Date: whenever")
    assert start is None
    assert end is None
