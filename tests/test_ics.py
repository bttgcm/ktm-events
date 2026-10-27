from scrapers.base import Event
from ics import build_calendar


def make_event(**overrides) -> Event:
    defaults = dict(
        title="Talk, with a comma",
        start="2026-09-29T15:00:00+05:45",
        source_name="Martin Chautari",
        source_url="https://martinchautari.org.np/events/x",
    )
    defaults.update(overrides)
    return Event(**defaults)


def test_build_calendar_contains_one_vevent_per_event():
    events = [make_event(), make_event(source_url="https://martinchautari.org.np/events/y")]
    calendar = build_calendar(events)

    assert calendar.count("BEGIN:VEVENT") == 2
    assert calendar.count("END:VEVENT") == 2
    assert calendar.startswith("BEGIN:VCALENDAR\r\n")
    assert calendar.endswith("END:VCALENDAR\r\n")


def test_start_time_is_converted_to_utc():
    calendar = build_calendar([make_event()])
    assert "DTSTART:20260929T091500Z" in calendar


def test_missing_end_defaults_to_one_hour_later():
    calendar = build_calendar([make_event()])
    assert "DTEND:20260929T101500Z" in calendar


def test_explicit_end_is_used_when_present():
    calendar = build_calendar([make_event(end="2026-09-29T16:30:00+05:45")])
    assert "DTEND:20260929T104500Z" in calendar


def test_special_characters_are_escaped():
    calendar = build_calendar([make_event(title="Talk, with a comma; and semicolon")])
    assert "SUMMARY:Talk\\, with a comma\\; and semicolon" in calendar
