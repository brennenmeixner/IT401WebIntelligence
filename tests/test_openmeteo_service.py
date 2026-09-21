import requests

from services import openmeteo_service
from tests.fake_response import FakeResponse


def test_get_marine_forecast_success(monkeypatch):
    fake_body = {
        "hourly": {"time": ["2026-01-01T00:00"], "wave_height": [1.2]},
        "hourly_units": {"wave_height": "m"},
    }
    monkeypatch.setattr(openmeteo_service.requests, "get", lambda *a, **k: FakeResponse(fake_body))

    result = openmeteo_service.get_marine_forecast(34.24, -119.26)

    assert result["live"] is True
    assert result["data"]["hourly"]["wave_height"] == [1.2]
    assert result["error"] is None


def test_get_marine_forecast_handles_request_exception(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(openmeteo_service.requests, "get", raise_exc)

    result = openmeteo_service.get_marine_forecast(34.24, -119.26)

    assert result["live"] is False
    assert result["data"] is None
    assert result["error"]


def test_get_weather_forecast_success(monkeypatch):
    fake_body = {
        "hourly": {"time": ["2026-01-01T00:00"], "temperature_2m": [18.4]},
        "hourly_units": {"temperature_2m": "°C"},
    }
    monkeypatch.setattr(openmeteo_service.requests, "get", lambda *a, **k: FakeResponse(fake_body))

    result = openmeteo_service.get_weather_forecast(34.24, -119.26)

    assert result["live"] is True
    assert result["data"]["hourly"]["temperature_2m"] == [18.4]


def test_get_weather_forecast_handles_request_exception(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(openmeteo_service.requests, "get", raise_exc)

    result = openmeteo_service.get_weather_forecast(34.24, -119.26)

    assert result["live"] is False
    assert result["data"] is None
