from scrapers.base import Event, EventSourceAdapter
import pipeline


def make_event(source_url: str, start: str) -> Event:
    return Event(
        title="t",
        start=start,
        source_name="Test Source",
        source_url=source_url,
    )


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
