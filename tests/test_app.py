import pytest

from app import create_app
from config import Config
from services.breaks_service import filter_breaks, find_break, load_breaks


@pytest.fixture
def client():
    app = create_app("development")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200


def test_explore(client):
    response = client.get("/explore")
    assert response.status_code == 200


def test_explore_with_filters(client):
    response = client.get("/explore?q=rincon&region=Santa+Barbara+County&wind=Glassy")
    assert response.status_code == 200
    assert b"Rincon" in response.data


def test_explore_no_matches_shows_empty_state(client):
    response = client.get("/explore?q=nonexistent-break-xyz")
    assert response.status_code == 200
    assert b"Flat. Nothing here." in response.data


def test_rewards(client):
    response = client.get("/rewards")
    assert response.status_code == 200


def test_filter_breaks_no_match_returns_empty_list():
    breaks = load_breaks(Config.DATA_DIR)
    assert filter_breaks(breaks, q="not-a-real-break") == []


def test_find_break_returns_matching_record():
    breaks = load_breaks(Config.DATA_DIR)
    result = find_break(breaks, "rincon")
    assert result is not None
    assert result["name"] == "Rincon"


def test_find_break_returns_none_for_unknown_id():
    breaks = load_breaks(Config.DATA_DIR)
    assert find_break(breaks, "not-a-real-id") is None


def test_explore_has_view_details_link(client):
    response = client.get("/explore")
    assert b"/break/" in response.data


def test_break_detail_known_id(client, monkeypatch):
    import routes.main as main_module
    from services.external_common import live_result

    def fake_panel(*args, **kwargs):
        empty = live_result("test-source", {})
        marine = live_result(
            "test-source",
            {
                "hourly": {
                    "time": ["2026-01-01T00:00"],
                    "wave_height": [1.0],
                    "swell_wave_height": [0.8],
                    "swell_wave_period": [13],
                    "wind_wave_height": [0.3],
                },
                "hourly_units": {},
            },
        )
        weather = live_result(
            "test-source",
            {
                "hourly": {
                    "time": ["2026-01-01T00:00"],
                    "temperature_2m": [18.0],
                    "wind_speed_10m": [10.0],
                    "wind_gusts_10m": [15.0],
                },
                "hourly_units": {"temperature_2m": "°C", "wind_speed_10m": "km/h", "wind_gusts_10m": "km/h"},
            },
        )
        return {
            "break": {"id": "south-jetty", "name": "South Jetty", "factors": "", "orientation": "SW", "location": "", "ndbc_station": "46053"},
            "marine": marine,
            "weather": weather,
            "nws_forecast": live_result("test-source", {"periods": [], "waves": {}}),
            "nws_alerts": live_result("test-source", []),
            "tide_predictions": live_result("test-source", []),
            "tide_curve": live_result("test-source", []),
            "water_temp": empty,
            "spc_outlook": live_result("test-source", {"active": False}),
            "radar": live_result("test-source", {"frames": [], "base_tile_url": ""}),
            "buoy_reading": empty,
        }

    monkeypatch.setattr(main_module, "build_break_panel", fake_panel)

    response = client.get("/break/south-jetty")
    assert response.status_code == 200
    assert b"South Jetty" in response.data


def test_break_detail_unknown_id(client):
    response = client.get("/break/not-a-real-id")
    assert response.status_code == 404
    assert b"not found" in response.data.lower()
