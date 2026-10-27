from datetime import datetime, timedelta, timezone

from scrapers.base import Event, EventSourceAdapter
import pipeline


def make_event(source_url: str, start: str, end: str | None = None) -> Event:
    return Event(
        title="t",
        start=start,
        end=end,
        source_name="Test Source",
        source_url=source_url,
    )


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def test_dedupe_keeps_one_event_per_id():
    events = [
        make_event("https://example.com/a", "2026-01-01T00:00:00+05:45"),
        make_event("https://example.com/a", "2026-01-01T00:00:00+05:45"),
        make_event("https://example.com/b", "2026-01-02T00:00:00+05:45"),
    ]
    result = pipeline.dedupe(events)
    assert len(result) == 2


def test_sort_by_start_orders_ascending():
    events = [
        make_event("https://example.com/late", "2026-03-01T00:00:00+05:45"),
        make_event("https://example.com/early", "2026-01-01T00:00:00+05:45"),
    ]
    result = pipeline.sort_by_start(events)
    assert [e.source_url for e in result] == [
        "https://example.com/early",
        "https://example.com/late",
    ]


def test_drop_stale_events_keeps_recent_and_future():
    now = datetime.now(timezone.utc)
    recent_past = make_event("https://example.com/recent", _iso(now - timedelta(days=5)))
    ancient_past = make_event("https://example.com/ancient", _iso(now - timedelta(days=400)))
    future = make_event("https://example.com/future", _iso(now + timedelta(days=5)))

    result = pipeline.drop_stale_events([recent_past, ancient_past, future])

    urls = {e.source_url for e in result}
    assert urls == {"https://example.com/recent", "https://example.com/future"}


def test_drop_stale_events_uses_end_when_present():
    now = datetime.now(timezone.utc)
    # Started long ago but still running (or ended recently) - should be kept.
    ongoing = make_event(
        "https://example.com/ongoing",
        _iso(now - timedelta(days=400)),
        end=_iso(now - timedelta(days=1)),
    )
    result = pipeline.drop_stale_events([ongoing])
    assert len(result) == 1


class FailingAdapter(EventSourceAdapter):
    name = "failing"

    def fetch_events(self) -> list[Event]:
        raise RuntimeError("simulated failure")


class WorkingAdapter(EventSourceAdapter):
    name = "working"

    def fetch_events(self) -> list[Event]:
        return [make_event("https://example.com/ok", "2026-01-01T00:00:00+05:45")]


def test_one_failing_adapter_does_not_block_others(monkeypatch):
    monkeypatch.setitem(pipeline.ADAPTERS, "failing", FailingAdapter)
    monkeypatch.setitem(pipeline.ADAPTERS, "working", WorkingAdapter)

    events = pipeline.collect_events(["failing", "working"])

    assert len(events) == 1
    assert events[0].source_url == "https://example.com/ok"
