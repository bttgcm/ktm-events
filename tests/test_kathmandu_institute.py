from pathlib import Path

from scrapers.kathmandu_institute import KathmanduInstituteAdapter

LISTING_HTML = (
    Path(__file__).parent / "fixtures" / "kathmandu_institute_monthly_events.html"
).read_text(encoding="utf-8")

DETAIL_HTML = (
    Path(__file__).parent / "fixtures" / "kathmandu_institute_detail.html"
).read_text(encoding="utf-8")

DETAIL_URL = "https://kathmanduinstitute.org.np/monthly-events/urban-space-aesthetics-and-media/"


def test_extract_event_urls_skips_months_without_a_link():
    urls = KathmanduInstituteAdapter._extract_event_urls(LISTING_HTML)

    assert urls == [DETAIL_URL]


def test_parse_detail_extracts_title_date_venue_and_speaker():
    adapter = KathmanduInstituteAdapter()
    event = adapter._parse_detail(DETAIL_URL, DETAIL_HTML)

    assert event is not None
    assert event.title == "Urban Space : Aesthetics and Media"
    assert event.start == "2025-06-27T00:00:00+05:45"
    assert event.location == "Conferece Hall, Sajha South Asia Centre, Pulchowk, Lalitpur."
    assert event.description == "Speaker: Kanak Mani Dixit"
    assert event.source_url == DETAIL_URL


def test_parse_detail_returns_none_without_date_field():
    adapter = KathmanduInstituteAdapter()
    event = adapter._parse_detail(
        DETAIL_URL,
        '<h2 class="elementor-heading-title">No Date Here</h2>',
    )
    assert event is None
