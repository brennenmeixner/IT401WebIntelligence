from services import forecast_service
from services.external_common import failed_result, live_result

BREAK = {
    "id": "south-jetty",
    "latitude": 34.24,
    "longitude": -119.26,
    "nws_office": "LOX",
    "nws_grid_x": 120,
    "nws_grid_y": 60,
    "ndbc_station": "46053",
    "coops_station": "9411340",
}

PANEL_KEYS = [
    "marine",
    "weather",
    "nws_forecast",
    "nws_alerts",
    "tide_predictions",
    "tide_curve",
    "water_temp",
    "spc_outlook",
    "radar",
    "buoy_reading",
]


def _patch_all_succeed(monkeypatch):
    for name in [
        "get_marine_forecast",
        "get_weather_forecast",
        "get_gridpoint_forecast",
        "get_active_alerts",
        "get_tide_predictions",
        "get_tide_curve",
        "get_water_temperature",
        "get_convective_outlook",
        "get_radar_frames",
        "scrape_latest_observation",
    ]:
        monkeypatch.setattr(
            forecast_service, name, lambda *a, **k: live_result("test-source", {"ok": True})
        )


def _patch_all_fail(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise RuntimeError("source is down")

    for name in [
        "get_marine_forecast",
        "get_weather_forecast",
        "get_gridpoint_forecast",
        "get_active_alerts",
        "get_tide_predictions",
        "get_tide_curve",
        "get_water_temperature",
        "get_convective_outlook",
        "get_radar_frames",
        "scrape_latest_observation",
    ]:
        monkeypatch.setattr(forecast_service, name, raise_exc)


def test_build_break_panel_all_sources_succeed(monkeypatch):
    _patch_all_succeed(monkeypatch)

    panel = forecast_service.build_break_panel(BREAK, nws_user_agent="test-agent")

    assert panel["break"] is BREAK
    for key in PANEL_KEYS:
        assert panel[key]["live"] is True


def test_build_break_panel_all_sources_fail_never_raises(monkeypatch):
    _patch_all_fail(monkeypatch)

    panel = forecast_service.build_break_panel(BREAK, nws_user_agent="test-agent")

    for key in PANEL_KEYS:
        assert panel[key]["live"] is False


def test_build_break_panel_partial_failure_isolated(monkeypatch):
    _patch_all_succeed(monkeypatch)
    monkeypatch.setattr(
        forecast_service,
        "scrape_latest_observation",
        lambda *a, **k: failed_result("NDBC", "station page unreachable"),
    )

    panel = forecast_service.build_break_panel(BREAK, nws_user_agent="test-agent")

    assert panel["buoy_reading"]["live"] is False
    assert panel["marine"]["live"] is True
    assert panel["tide_curve"]["live"] is True
