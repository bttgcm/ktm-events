from pathlib import Path

from scrapers.taragaon_next import TaragaonNextAdapter

FIXTURE_HTML = (
    Path(__file__).parent / "fixtures" / "taragaon_next_whats_on.html"
).read_text(encoding="utf-8")


def test_parse_listing_extracts_events_with_categories_and_dedupes():
    adapter = TaragaonNextAdapter()
    events = adapter._parse_listing(FIXTURE_HTML)

    assert len(events) > 0
    urls = [e.source_url for e in events]
    assert len(urls) == len(set(urls)), "expected no duplicate events"

    heritage_walk = next(e for e in events if "Heritage Walk" in e.title)
    assert heritage_walk.start == "2026-09-13T07:00:00+05:45"
    assert heritage_walk.categories == ["Events"]
    assert heritage_walk.source_url == (
        "https://taragaonnext.com/events/heritage-walk-to-chabahi-with-saurav-thapa-shrestha/"
    )


def test_parse_date_handles_minutes_and_bare_hour():
    assert (
        TaragaonNextAdapter._parse_date("September 18, 2026 | 4:00 p.m.")
        == "2026-09-18T16:00:00+05:45"
    )
    assert TaragaonNextAdapter._parse_date("September 13, 2026 | 7 a.m.") == "2026-09-13T07:00:00+05:45"


def test_parse_date_returns_none_for_unrecognized_text():
    assert TaragaonNextAdapter._parse_date("sometime soon") is None
