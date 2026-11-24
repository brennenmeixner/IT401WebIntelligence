import os

import requests

from services import buoy_scraper_service
from tests.fake_response import FakeResponse

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _read_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name), encoding="utf-8") as f:
        return f.read()


def test_scrape_latest_observation_extracts_expected_fields(monkeypatch):
    html = _read_fixture("ndbc_sample.html")
    monkeypatch.setattr(
        buoy_scraper_service.requests, "get", lambda *a, **k: FakeResponse(text=html)
    )

    result = buoy_scraper_service.scrape_latest_observation("46053")

    assert result["live"] is True
    data = result["data"]
    assert data["wave_height_ft"] == 2.0
    assert data["dominant_period_s"] == 13
    assert data["wind_speed_kt"] == 11.7
    assert data["water_temp_f"] == 69.8
    assert data["pressure_in"] == 29.91
    assert "W" in data["wind_direction"]


def test_scrape_latest_observation_missing_fields_degrades_gracefully(monkeypatch):
    html = _read_fixture("ndbc_missing_fields.html")
    monkeypatch.setattr(
        buoy_scraper_service.requests, "get", lambda *a, **k: FakeResponse(text=html)
    )

    result = buoy_scraper_service.scrape_latest_observation("venf1")

    assert result["live"] is True
    data = result["data"]
    assert "wave_height_ft" not in data
    assert "dominant_period_s" not in data
    assert data["wind_speed_kt"] == 3


def test_scrape_latest_observation_request_failure(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(buoy_scraper_service.requests, "get", raise_exc)

    result = buoy_scraper_service.scrape_latest_observation("46053")

    assert result["live"] is False
    assert result["data"] is None
