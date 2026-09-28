from pathlib import Path

import requests

from scrapers.martin_chautari import MartinChautariAdapter

FIXTURE_HTML = (
    Path(__file__).parent / "fixtures" / "martin_chautari_events.html"
).read_text(encoding="utf-8")

DETAIL_HTML_WITH_MULTILINE_DESCRIPTION = """
<html><body>
<script type="application/ld+json">
{"@type": "", "description": "line one", "image": ["https://example.com/img-not-found.png"]}
</script>
<script type="application/ld+json">
{
    "@type": "Event",
    "description": "line one
line two",
    "image": ["https://example.com/real.jpg"],
    "location": {"@type": "Place", "name": "", "address": "Martin Chautari, Kathmandu"}
}
</script>
</body></html>
"""


def test_parse_listing_extracts_both_events():
    adapter = MartinChautariAdapter()
    events = adapter._parse_listing(FIXTURE_HTML)

    assert len(events) == 2

    single_day = events[0]
    assert "भोटेकोशी" in single_day.title
    assert single_day.start == "2026-09-29T15:00:00+05:45"
    assert single_day.end is None
    assert single_day.categories == ["Discussion", "Mangalbaarey"]
    assert single_day.description == "Speaker: अजय दीक्षित"
    assert single_day.source_url == (
        "https://martinchautari.org.np/events/"
        "hydropower-after-the-Bhotekoshi-Trishuli-disaster-Rethinking-the-fundamentals"
    )

    multi_day = events[1]
    assert multi_day.start == "2026-11-25T09:00:00+05:45"
    assert multi_day.end == "2026-11-27T17:00:00+05:45"
    assert multi_day.description is None


def test_extract_ld_json_merges_blocks_and_tolerates_raw_newlines():
    data = MartinChautariAdapter._extract_ld_json(DETAIL_HTML_WITH_MULTILINE_DESCRIPTION)

    assert data["description"] == "line one\nline two"
    assert data["location"]["address"] == "Martin Chautari, Kathmandu"


def test_apply_detail_data_skips_placeholder_image_and_blank_address():
    from scrapers.base import Event

    event = Event(
        title="t",
        start="2026-01-01T00:00:00+05:45",
        source_name="Martin Chautari",
        source_url="https://martinchautari.org.np/events/x",
    )
    data = {
        "description": "real description",
        "image": ["https://martinchautari.org.np/storage/img-not-found.png"],
        "location": {"address": ""},
    }
    MartinChautariAdapter._apply_detail_data(event, data)

    assert event.description == "real description"
    assert event.image is None
    assert event.location is None


def test_enrichment_failure_keeps_listing_page_data(monkeypatch):
    adapter = MartinChautariAdapter()
    events = adapter._parse_listing(FIXTURE_HTML)
    target = events[0]
    original_description = target.description

    def raise_connection_error(*args, **kwargs):
        raise requests.ConnectionError("simulated network failure")

    monkeypatch.setattr(requests, "get", raise_connection_error)
    adapter._enrich_from_detail_page(target)

    assert target.description == original_description
