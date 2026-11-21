from pathlib import Path

from scrapers.suggested_events import FORM_URL, SuggestedEventsAdapter

FIXTURE_CSV = (Path(__file__).parent / "fixtures" / "suggested_events.csv").read_text(encoding="utf-8")


def test_parse_csv_only_includes_approved_rows():
    adapter = SuggestedEventsAdapter()
    events = adapter._parse_csv(FIXTURE_CSV)

    titles = [e.title for e in events]
    assert "a measure of civilisation: the making of Newar Architecture History" in titles
    assert "a" not in titles  # Approved = FALSE
    assert "Pending review talk" not in titles  # Approved left blank
    assert "Unparseable date" not in titles  # bad date, rejected despite being approved


def test_approved_row_maps_fields_correctly():
    adapter = SuggestedEventsAdapter()
    events = adapter._parse_csv(FIXTURE_CSV)
    event = next(e for e in events if "Newar Architecture" in e.title)

    assert event.start == "2026-11-23T16:00:00+05:45"
    assert event.location == "YalaMal, Patan Dhoka, Kathmandu"
    assert event.source_url == "https://example.com/newar-architecture"
    assert event.source_name == "Community Suggestions"
    assert event.description == "A talk on Newar architectural history."


def test_approved_row_without_link_falls_back_to_form_url():
    adapter = SuggestedEventsAdapter()
    events = adapter._parse_csv(FIXTURE_CSV)
    event = next(e for e in events if e.title == "No link provided talk")

    assert event.source_url == FORM_URL


def test_approved_row_without_time_defaults_to_midnight():
    adapter = SuggestedEventsAdapter()
    events = adapter._parse_csv(FIXTURE_CSV)
    event = next(e for e in events if e.title == "No time given")

    assert event.start == "2026-12-06T00:00:00+05:45"


def test_parse_datetime_handles_valid_and_invalid_input():
    parse = SuggestedEventsAdapter._parse_datetime
    assert parse("23/11/2026", "16:00:00") == "2026-11-23T16:00:00+05:45"
    assert parse("23/11/2026", "") == "2026-11-23T00:00:00+05:45"
    assert parse("", "16:00:00") is None
    assert parse("not-a-date", "16:00:00") is None
