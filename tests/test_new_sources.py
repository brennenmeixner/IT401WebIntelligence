"""Tests for the four sources added in A3. No network: requests.get is faked."""

import requests

from services import beach_quality_service, ndbc_realtime_service, rapidapi_marine_service, usno_service
from tests.fake_response import FakeResponse

NDBC_TEXT = """#YY  MM DD hh mm WDIR WSPD GST  WVHT   DPD   APD MWD   PRES  ATMP  WTMP  DEWP  VIS PTDY  TIDE
#yr  mo dy hr mn degT m/s  m/s     m   sec   sec degT   hPa  degC  degC  degC  nmi  hPa    ft
2026 11 02 00 10 300 11.0 14.0   1.8    MM   5.2 264 1012.0  18.9  23.3  12.2   MM   MM    MM
2026 11 02 00 00 300 12.0 14.0    MM    MM    MM  MM 1011.8  18.9  23.3  11.6   MM +0.6    MM
2026 11 01 23 50 300 11.0 14.0   1.7     5   5.0 273 1011.8  19.0  23.3  12.2   MM   MM    MM
"""


# --- RapidAPI (WeatherAPI.com marine) ----------------------------------------

RAPID_BODY = {
    "location": {"name": "Ventura"},
    "forecast": {"forecastday": [{
        "day": {"tides": [{"tide": [{"tide_time": "2026-11-01 05:12", "tide_height_mt": "1.4", "tide_type": "HIGH"}]}]},
        "hour": [{"time": "2026-11-01 00:00", "sig_ht_mt": "1.2", "swell_ht_ft": "3.9",
                  "swell_period_secs": "13.1", "swell_dir_16_point": "WSW", "wind_kph": "12.0",
                  "wind_dir": "W", "water_temp_f": "61.0"}],
    }]},
}


def test_rapidapi_without_key_does_not_call(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    result = rapidapi_marine_service.get_marine_second_opinion(34.2, -119.2, api_key=None)
    assert result["live"] is False
    assert "RAPIDAPI_KEY" in result["error"]


def test_rapidapi_parses_hours_and_tides(monkeypatch):
    seen = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        seen["headers"] = headers
        return FakeResponse(RAPID_BODY)

    monkeypatch.setattr(requests, "get", fake_get)
    result = rapidapi_marine_service.get_marine_second_opinion(34.2, -119.2, api_key="k")
    assert result["live"] is True
    assert result["data"]["hours"][0]["swell_height_ft"] == 3.9
    assert result["data"]["tides"][0]["type"] == "HIGH"
    assert seen["headers"]["X-RapidAPI-Host"] == "weatherapi-com.p.rapidapi.com"


def test_rapidapi_http_error_hides_details(monkeypatch):
    def fake_get(*a, **k):
        resp = FakeResponse({}, status_code=403)
        resp.response = resp
        return resp

    monkeypatch.setattr(requests, "get", fake_get)
    result = rapidapi_marine_service.get_marine_second_opinion(34.2, -119.2, api_key="secret-key")
    assert result["live"] is False
    assert "secret-key" not in result["error"]


# --- NDBC realtime feed ---------------------------------------------------------

def test_ndbc_feed_skips_rows_without_waves_and_converts_units():
    rows = ndbc_realtime_service.parse_realtime_text(NDBC_TEXT)
    assert len(rows) == 2  # the 00:00 row has WVHT=MM
    assert rows[0]["wave_height_ft"] == 5.9  # 1.8 m
    assert rows[0]["dominant_period_s"] is None  # "MM"
    assert rows[1]["dominant_period_s"] == 5.0
    assert rows[0]["water_temp_f"] == 73.9


def test_ndbc_feed_bad_format_is_a_failed_result(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(text="<html>404</html>"))
    result = ndbc_realtime_service.get_realtime_observations("46053")
    assert result["live"] is False


# --- USNO sun/moon -------------------------------------------------------------

def test_usno_parses_sun_and_moon(monkeypatch):
    body = {"properties": {"data": {
        "curphase": "Third Quarter", "fracillum": "50%",
        "sundata": [{"phen": "Begin Civil Twilight", "time": "05:51"}, {"phen": "Rise", "time": "06:17"},
                    {"phen": "Set", "time": "17:04"}, {"phen": "End Civil Twilight", "time": "17:30"}],
    }}}
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(body))
    result = usno_service.get_sun_moon(34.2, -119.2)
    assert result["live"] is True
    assert result["data"]["first_light"] == "05:51"
    assert result["data"]["moon_phase"] == "Third Quarter"


def test_usno_unexpected_shape_is_a_failed_result(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse({"error": "bad"}))
    assert usno_service.get_sun_moon(34.2, -119.2)["live"] is False


# --- Beach Watch advisories ----------------------------------------------------

def test_only_nearby_advisories_are_kept():
    records = [
        {"DateofAdvisory": "2026-03-03", "Station_Description": "Surfer's Knoll", "Station_UpperLat": 34.2397, "Station_UpperLon": -119.2668},
        {"DateofAdvisory": "2026-03-01", "Station_Description": "Far away", "Station_UpperLat": 34.9, "Station_UpperLon": -120.6},
        {"DateofAdvisory": "2026-02-01", "Station_Description": "No coords"},
    ]
    nearby = beach_quality_service.nearby_advisories(records, 34.2406, -119.2646)
    assert [a["station"] for a in nearby] == ["Surfer's Knoll"]
    assert nearby[0]["distance_km"] < 1


def test_unknown_region_is_a_failed_result():
    result = beach_quality_service.get_beach_advisories("Orange County", 33.6, -117.9)
    assert result["live"] is False


def test_beach_api_success_false_is_a_failed_result(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse({"success": False}))
    assert beach_quality_service.get_beach_advisories("Ventura County", 34.2, -119.2)["live"] is False
