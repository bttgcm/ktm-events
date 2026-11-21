"""Fetches today's Kathmandu weather once per pipeline run and maps it
to a background gradient color (and whether to show a rain effect) for
the static site. Uses Open-Meteo, which needs no API key.

If the fetch fails, the caller should just leave yesterday's
docs/weather.json in place - same graceful-degradation approach as a
scraper source failing.
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

KATHMANDU_LATITUDE = 27.7172
KATHMANDU_LONGITUDE = 85.3240
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 10

# WMO weather codes - https://open-meteo.com/en/docs
SUNNY_CODES = {0, 1}
CLOUDY_CODES = {2, 3, 45, 48}
RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
SNOW_CODES = {71, 73, 75, 77, 85, 86}

CONDITION_COLORS = {
    "sunny": "#F4B400",
    "cloudy": "#9AA0A6",
    "rain": "#5C7A99",
    "snow": "#CFE2F3",
}


def classify(weather_code: int) -> str:
    if weather_code in RAIN_CODES:
        return "rain"
    if weather_code in SNOW_CODES:
        return "snow"
    if weather_code in CLOUDY_CODES:
        return "cloudy"
    if weather_code in SUNNY_CODES:
        return "sunny"
    return "cloudy"  # unrecognized code - a safe, unobtrusive default


def fetch_weather() -> Optional[dict]:
    try:
        response = requests.get(
            WEATHER_API_URL,
            params={
                "latitude": KATHMANDU_LATITUDE,
                "longitude": KATHMANDU_LONGITUDE,
                "current_weather": "true",
                "timezone": "Asia/Kathmandu",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        weather_code = response.json()["current_weather"]["weathercode"]
    except (requests.RequestException, KeyError, ValueError, TypeError) as exc:
        logger.warning("Weather fetch failed: %s", exc)
        return None

    condition = classify(weather_code)
    return {
        "condition": condition,
        "gradient_top": CONDITION_COLORS[condition],
        "weather_code": weather_code,
    }
