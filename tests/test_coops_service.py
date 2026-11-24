import requests

from services import coops_service
from tests.fake_response import FakeResponse


def test_get_tide_predictions_success(monkeypatch):
    body = {"predictions": [{"t": "2026-01-01 08:00", "v": "3.8", "type": "H"}]}
    monkeypatch.setattr(coops_service.requests, "get", lambda *a, **k: FakeResponse(body))

    result = coops_service.get_tide_predictions("9411340")

    assert result["live"] is True
    assert result["data"][0]["type"] == "H"
    assert result["data"][0]["height_ft"] == 3.8


def test_get_tide_predictions_request_failure(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(coops_service.requests, "get", raise_exc)

    result = coops_service.get_tide_predictions("9411340")

    assert result["live"] is False


def test_get_tide_curve_success(monkeypatch):
    body = {"predictions": [{"t": "2026-01-01 00:00", "v": "0.7"}]}
    monkeypatch.setattr(coops_service.requests, "get", lambda *a, **k: FakeResponse(body))

    result = coops_service.get_tide_curve("9411340")

    assert result["live"] is True
    assert result["data"][0]["height_ft"] == 0.7


def test_get_water_temperature_success(monkeypatch):
    body = {"data": [{"t": "2026-01-01 12:00", "v": "68.4", "f": "0,0,0"}]}
    monkeypatch.setattr(coops_service.requests, "get", lambda *a, **k: FakeResponse(body))

    result = coops_service.get_water_temperature("9410840")

    assert result["live"] is True
    assert result["data"]["value_f"] == 68.4


def test_get_water_temperature_unsupported_station_soft_error(monkeypatch):
    # CO-OPS returns HTTP 200 with an "error" body when a station has no
    # water-temperature sensor -- confirmed live against station 9411340.
    body = {"error": {"message": "No data was found. This product may not be offered here."}}
    monkeypatch.setattr(coops_service.requests, "get", lambda *a, **k: FakeResponse(body))

    result = coops_service.get_water_temperature("9411340")

    assert result["live"] is False
    assert "product" in result["error"] or "No data" in result["error"]
