import requests

from services import spc_service
from tests.fake_response import FakeResponse


def test_get_convective_outlook_success_active(monkeypatch):
    body = {
        "outlooks": [
            {
                "day": 1,
                "utc_issue": "2099-01-01T12:00:00Z",
                "utc_expire": "2099-01-02T12:00:00Z",
                "threshold": "SLGT",
                "category": "CATEGORICAL",
            }
        ]
    }
    monkeypatch.setattr(spc_service.requests, "get", lambda *a, **k: FakeResponse(body))

    result = spc_service.get_convective_outlook(34.24, -119.26)

    assert result["live"] is True
    assert result["data"]["active"] is True
    assert result["data"]["threshold"] == "SLGT"


def test_get_convective_outlook_expired_entry_is_not_active(monkeypatch):
    body = {
        "outlooks": [
            {
                "day": 1,
                "utc_issue": "2020-01-01T12:00:00Z",
                "utc_expire": "2020-01-02T12:00:00Z",
                "threshold": "SLGT",
                "category": "CATEGORICAL",
            }
        ]
    }
    monkeypatch.setattr(spc_service.requests, "get", lambda *a, **k: FakeResponse(body))

    result = spc_service.get_convective_outlook(34.24, -119.26)

    assert result["live"] is True
    assert result["data"]["active"] is False


def test_get_convective_outlook_empty_history_is_not_active(monkeypatch):
    monkeypatch.setattr(
        spc_service.requests, "get", lambda *a, **k: FakeResponse({"outlooks": []})
    )

    result = spc_service.get_convective_outlook(34.24, -119.26)

    assert result["live"] is True
    assert result["data"]["active"] is False


def test_get_convective_outlook_request_failure(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(spc_service.requests, "get", raise_exc)

    result = spc_service.get_convective_outlook(34.24, -119.26)

    assert result["live"] is False


def test_get_convective_outlook_unexpected_shape_does_not_raise(monkeypatch):
    monkeypatch.setattr(spc_service.requests, "get", lambda *a, **k: FakeResponse({}))

    result = spc_service.get_convective_outlook(34.24, -119.26)

    assert result["live"] is True
    assert result["data"]["active"] is False
