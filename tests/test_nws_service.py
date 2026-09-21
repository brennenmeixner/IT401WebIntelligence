import requests

from services import nws_service
from tests.fake_response import FakeResponse

FORECAST_BODY = {
    "properties": {
        "periods": [
            {
                "name": "Today",
                "temperature": 70,
                "temperatureUnit": "F",
                "windSpeed": "10 mph",
                "windDirection": "W",
                "shortForecast": "Sunny",
                "icon": "https://api.weather.gov/icons/land/day/skc",
            }
        ]
    }
}
RAW_GRID_BODY = {
    "properties": {
        "waveHeight": {"uom": "wmoUnit:m", "values": [{"validTime": "2026-01-01T00:00Z/PT1H", "value": 1.0}]},
        "wavePeriod": {"uom": "wmoUnit:s", "values": [{"validTime": "2026-01-01T00:00Z/PT1H", "value": 13}]},
    }
}


def test_get_gridpoint_forecast_success(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/forecast"):
            return FakeResponse(FORECAST_BODY)
        return FakeResponse(RAW_GRID_BODY)

    monkeypatch.setattr(nws_service.requests, "get", fake_get)

    result = nws_service.get_gridpoint_forecast("LOX", 120, 60, "test-agent")

    assert result["live"] is True
    assert result["data"]["periods"][0]["name"] == "Today"
    assert result["data"]["waves"]["waveHeight"]["value"] == 1.0


def test_get_gridpoint_forecast_filters_unpopulated_zero_placeholders(monkeypatch):
    # NWS often reports a literal 0 for waveHeight/wavePeriod on nearshore
    # grid points it doesn't actually cover -- confirmed live against a
    # real LOX gridpoint. That should read as "not published", not "flat".
    zero_grid_body = {
        "properties": {
            "waveHeight": {"uom": "wmoUnit:m", "values": [{"validTime": "t", "value": 0}]},
            "wavePeriod": {"uom": "wmoUnit:s", "values": [{"validTime": "t", "value": 0}]},
        }
    }

    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/forecast"):
            return FakeResponse(FORECAST_BODY)
        return FakeResponse(zero_grid_body)

    monkeypatch.setattr(nws_service.requests, "get", fake_get)

    result = nws_service.get_gridpoint_forecast("LOX", 113, 67, "test-agent")

    assert result["live"] is True
    assert result["data"]["waves"] == {}


def test_get_gridpoint_forecast_request_failure(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(nws_service.requests, "get", raise_exc)

    result = nws_service.get_gridpoint_forecast("LOX", 120, 60, "test-agent")

    assert result["live"] is False
    assert result["data"] is None


def test_get_active_alerts_success(monkeypatch):
    body = {
        "features": [
            {
                "properties": {
                    "event": "High Surf Advisory",
                    "headline": "High Surf Advisory issued",
                    "severity": "Moderate",
                    "effective": "2026-01-01T00:00:00Z",
                    "expires": "2026-01-02T00:00:00Z",
                }
            }
        ]
    }
    monkeypatch.setattr(nws_service.requests, "get", lambda *a, **k: FakeResponse(body))

    result = nws_service.get_active_alerts(34.24, -119.26, "test-agent")

    assert result["live"] is True
    assert result["data"][0]["event"] == "High Surf Advisory"


def test_get_active_alerts_empty_list_when_none_active(monkeypatch):
    monkeypatch.setattr(
        nws_service.requests, "get", lambda *a, **k: FakeResponse({"features": []})
    )

    result = nws_service.get_active_alerts(34.24, -119.26, "test-agent")

    assert result["live"] is True
    assert result["data"] == []


def test_get_active_alerts_request_failure(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(nws_service.requests, "get", raise_exc)

    result = nws_service.get_active_alerts(34.24, -119.26, "test-agent")

    assert result["live"] is False
