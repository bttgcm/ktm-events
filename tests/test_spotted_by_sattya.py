from datetime import datetime
from pathlib import Path

from scrapers.spotted_by_sattya import SpottedBySattyaAdapter

FIXTURE_BYTES = (
    Path(__file__).parent / "fixtures" / "spotted_by_sattya_posts.json"
).read_bytes()


def test_parse_feed_extracts_events_from_the_digest():
    adapter = SpottedBySattyaAdapter()
    events = adapter._parse_feed(FIXTURE_BYTES)

    assert len(events) > 0

    film_talk = next(e for e in events if "knowledge-making beyond text" in e.title)
    assert film_talk.start == "2026-09-25T16:30:00+05:45"
    assert film_talk.categories == ["Film"]
    assert film_talk.source_url.startswith("https://www.instagram.com/p/Ddnuq1IDXBr/?img_index=1")
    assert "Yalamaya Kendra" in film_talk.description


def test_events_within_a_day_get_distinct_ids_even_without_a_link():
    adapter = SpottedBySattyaAdapter()
    events = adapter._parse_feed(FIXTURE_BYTES)
    ids = [e.id for e in events]
    assert len(ids) == len(set(ids)), "expected every event to have a unique id"


def test_parse_day_heading_infers_year_from_reference_date():
    reference = datetime(2026, 9, 28, 3, 0, 0)
    day = SpottedBySattyaAdapter._parse_day_heading("friday – september 25", reference)
    assert day is not None
    assert (day.year, day.month, day.day) == (2026, 9, 25)


def test_combine_date_and_time_handles_bare_hour_and_minutes():
    day = datetime(2026, 9, 25)
    assert (
        SpottedBySattyaAdapter._combine_date_and_time(day, "4:30pm")
        == "2026-09-25T16:30:00+05:45"
    )
    assert (
        SpottedBySattyaAdapter._combine_date_and_time(day, "7pm")
        == "2026-09-25T19:00:00+05:45"
    )
