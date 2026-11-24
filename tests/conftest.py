"""Shared pytest fixtures.

Every test gets a fresh app on TestConfig: an in-memory SQLite database
(never the real MySQL), CSRF off, and no API keys. Tables are created
before each test and dropped after, so tests can't affect each other.
"""

import pytest

from app import create_app
from extensions import db as _db


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def south_jetty():
    """A break record shaped like data/breaks.json."""
    return {
        "id": "south-jetty",
        "name": "South Jetty",
        "location": "Ventura County",
        "region": "Ventura County",
        "orientation": "SW",
        "factors": "",
        "latitude": 34.2406,
        "longitude": -119.2646,
        "nws_office": "LOX",
        "nws_grid_x": 120,
        "nws_grid_y": 60,
        "ndbc_station": "46053",
        "coops_station": "9411340",
    }


@pytest.fixture
def fake_panel(south_jetty):
    """A break panel where every source is live with small, realistic data."""
    from services.external_common import failed_result, live_result

    def build(**overrides):
        panel = {
            "break": south_jetty,
            "marine": live_result("Open-Meteo Marine Weather API", {
                "hourly": {
                    "time": ["2026-01-01T00:00"],
                    "wave_height": [1.0],
                    "swell_wave_height": [0.8],
                    "swell_wave_period": [13],
                    "wind_wave_height": [0.3],
                },
                "hourly_units": {},
            }),
            "weather": live_result("Open-Meteo Weather Forecast API", {
                "hourly": {
                    "time": ["2026-01-01T00:00"],
                    "temperature_2m": [18.0],
                    "wind_speed_10m": [10.0],
                    "wind_gusts_10m": [15.0],
                },
                "hourly_units": {"temperature_2m": "°C", "wind_speed_10m": "km/h", "wind_gusts_10m": "km/h"},
            }),
            "nws_forecast": live_result("NOAA NWS", {"periods": [], "waves": {}}),
            "nws_alerts": live_result("NOAA NWS Alerts", []),
            "tide_predictions": live_result("CO-OPS", [{"time": "2026-01-01 05:00", "type": "H", "height_ft": 4.2}]),
            "tide_curve": live_result("CO-OPS", []),
            "water_temp": failed_result("CO-OPS", "no sensor"),
            "spc_outlook": live_result("SPC", {"active": False}),
            "radar": live_result("RainViewer", {"frames": [], "base_tile_url": ""}),
            "buoy_reading": live_result("NDBC scrape", {"wave_height_ft": 5.9, "dominant_period_s": 7.0}),
            "buoy_history": live_result("NDBC feed", {
                "station": "46053",
                "rows": [{"time_utc": "2026-01-01T00:20Z", "wave_height_ft": 5.9, "dominant_period_s": 7.0,
                          "average_period_s": 5.2, "wave_direction_deg": 264.0, "wind_speed_kt": 21.4,
                          "water_temp_f": 60.1}],
                "latest": {"time_utc": "2026-01-01T00:20Z", "wave_height_ft": 5.9, "dominant_period_s": 7.0},
            }),
            "rapid_marine": failed_result("RapidAPI", "RAPIDAPI_KEY is not set in .env"),
            "sun_moon": live_result("USNO", {"first_light": "05:51", "sunrise": "06:17", "sunset": "17:04",
                                             "last_light": "17:30", "moon_phase": "Third Quarter",
                                             "moon_illumination": "50%", "date": "2026-11-01"}),
            "beach_quality": live_result("Beach Watch", {"county": "Ventura", "latest_record_date": "2026-03-03",
                                                         "advisories": [], "radius_km": 5.0}),
        }
        panel.update(overrides)
        return panel

    return build
