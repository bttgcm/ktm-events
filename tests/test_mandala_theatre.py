from pathlib import Path

from scrapers.mandala_theatre import MandalaTheatreAdapter

ARCHIVE_HTML = (
    Path(__file__).parent / "fixtures" / "mandala_theatre_events_archive.html"
).read_text(encoding="utf-8")

DETAIL_HTML = (
    Path(__file__).parent / "fixtures" / "mandala_theatre_detail.html"
).read_text(encoding="utf-8")

DETAIL_URL = "https://www.mandalatheatre.com/events/the-age-of-darkness/"


def test_extract_event_urls_excludes_the_archive_itself():
    urls = MandalaTheatreAdapter._extract_event_urls(ARCHIVE_HTML)

    assert len(urls) > 0
    assert all("mandalatheatre.com" not in u or u.rstrip("/") != "https://www.mandalatheatre.com/events" for u in urls)
    assert DETAIL_URL in urls
    assert len(urls) == len(set(urls))


def test_parse_detail_extracts_title_dates_and_category():
    adapter = MandalaTheatreAdapter()
    event = adapter._parse_detail(DETAIL_URL, DETAIL_HTML)

    assert event is not None
    assert event.title == "The Age of Darkness"
    assert event.start == "2026-08-07T00:00:00+05:45"
    assert event.end == "2026-08-30T00:00:00+05:45"
    assert event.categories == ["Theatre"]
    assert event.source_url == DETAIL_URL


def test_parse_detail_returns_none_without_starts_on_field():
    adapter = MandalaTheatreAdapter()
    event = adapter._parse_detail(DETAIL_URL, "<html><body>no date info here</body></html>")
    assert event is None
