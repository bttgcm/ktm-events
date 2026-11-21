import requests

import weather


def test_classify_maps_known_codes():
    assert weather.classify(0) == "sunny"
    assert weather.classify(3) == "cloudy"
    assert weather.classify(61) == "rain"
    assert weather.classify(95) == "rain"
    assert weather.classify(73) == "snow"


def test_classify_falls_back_to_cloudy_for_unknown_code():
    assert weather.classify(12345) == "cloudy"


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_weather_returns_mapped_condition(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return FakeResponse({"current_weather": {"weathercode": 61}})

    monkeypatch.setattr(weather.requests, "get", fake_get)

    result = weather.fetch_weather()
    assert result == {"condition": "rain", "gradient_top": "#5C7A99", "weather_code": 61}


def test_fetch_weather_returns_none_on_request_failure(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise requests.RequestException("boom")

    monkeypatch.setattr(weather.requests, "get", fake_get)

    assert weather.fetch_weather() is None


def test_fetch_weather_returns_none_on_malformed_response(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return FakeResponse({"unexpected": "shape"})

    monkeypatch.setattr(weather.requests, "get", fake_get)

    assert weather.fetch_weather() is None
