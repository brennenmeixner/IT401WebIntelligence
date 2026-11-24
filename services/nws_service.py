"""NOAA NWS API (api.weather.gov) -- no API key, just a descriptive User-Agent.

Docs: https://www.weather.gov/documentation/services-web-api

Combines two endpoints per break:
- /gridpoints/{office}/{x},{y}/forecast -- human-readable periods (temp,
  wind, short forecast text, icon).
- /gridpoints/{office}/{x},{y} (raw) -- numeric wave/swell values, which
  are NOT present in the /forecast endpoint above.
"""

import requests

from services.external_common import failed_result, live_result

SOURCE_FORECAST = "NOAA NWS Gridpoint Forecast"
SOURCE_ALERTS = "NOAA NWS Active Alerts"

BASE_URL = "https://api.weather.gov"

# field -> (human label, kind). NWS raw grid data is always SI (meters,
# degrees, seconds) regardless of what its "uom" string says, so the kind
# drives how _friendly_wave_value converts it for display.
WAVE_FIELD_META = {
    "waveHeight": ("Wave height", "height"),
    "wavePeriod": ("Wave period", "seconds"),
    "waveDirection": ("Wave direction", "degrees"),
    "primarySwellHeight": ("Primary swell height", "height"),
    "primarySwellDirection": ("Primary swell direction", "degrees"),
    "secondarySwellHeight": ("Secondary swell height", "height"),
    "secondarySwellDirection": ("Secondary swell direction", "degrees"),
    "wavePeriod2": ("Secondary swell period", "seconds"),
    "windWaveHeight": ("Wind wave height", "height"),
}
WAVE_FIELDS = list(WAVE_FIELD_META)

COMPASS_POINTS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]  # fmt: skip


def _first_value(layer):
    """Pull the first timeseries reading out of an NWS raw gridpoint data layer."""
    if not isinstance(layer, dict):
        return None
    values = layer.get("values") or []
    if not values or values[0].get("value") is None:
        return None
    return {"value": values[0]["value"], "unit": layer.get("uom")}


def _friendly_wave_value(field, raw):
    """Add a human-readable label/value/unit to a raw NWS wave reading.

    Keeps the original value/unit untouched (SI, as NWS publishes it) and
    adds display_value/display_unit converted to feet/compass-degrees for
    the template, since raw meters and "wmoUnit:m"-style unit strings
    aren't readable on their own.
    """
    label, kind = WAVE_FIELD_META.get(field, (field, "raw"))
    value = raw["value"]
    if kind == "height":
        display_value = round(value * 3.28084, 1)
        display_unit = "ft"
    elif kind == "seconds":
        display_value = round(value, 1)
        display_unit = "s"
    elif kind == "degrees":
        compass = COMPASS_POINTS[round(value / 22.5) % 16]
        display_value = f"{round(value)}° ({compass})"
        display_unit = ""
    else:
        display_value = value
        display_unit = raw.get("unit", "")
    return {"label": label, "value": value, "unit": raw["unit"], "display_value": display_value, "display_unit": display_unit}


def get_gridpoint_forecast(office, grid_x, grid_y, user_agent, timeout=10):
    """Fetch NWS forecast periods plus raw wave/swell data for one gridpoint.

    Returns the standard {live, source, data, fetched_at, error} dict, with
    data = {"periods": [...], "waves": {...}}. Missing wave fields are
    simply omitted from "waves" rather than causing a failure -- not every
    NWS office/grid publishes marine wave data.
    """
    headers = {"User-Agent": user_agent, "Accept": "application/geo+json"}
    base = f"{BASE_URL}/gridpoints/{office}/{grid_x},{grid_y}"
    try:
        forecast_resp = requests.get(f"{base}/forecast", headers=headers, timeout=timeout)
        forecast_resp.raise_for_status()
        periods = forecast_resp.json()["properties"]["periods"][:4]
        simplified_periods = [
            {
                "name": p.get("name"),
                "temperature": p.get("temperature"),
                "temperature_unit": p.get("temperatureUnit"),
                "wind_speed": p.get("windSpeed"),
                "wind_direction": p.get("windDirection"),
                "short_forecast": p.get("shortForecast"),
                "icon": p.get("icon"),
            }
            for p in periods
        ]

        raw_resp = requests.get(base, headers=headers, timeout=timeout)
        raw_resp.raise_for_status()
        raw_props = raw_resp.json().get("properties", {})
        waves = {}
        for field in WAVE_FIELDS:
            value = _first_value(raw_props.get(field))
            if value is None:
                continue
            _label, kind = WAVE_FIELD_META[field]
            # NWS often reports an unpopulated "0" placeholder for
            # nearshore land grid points its marine forecast doesn't
            # actually cover -- a literal 0 ft / 0 s reading isn't a real
            # forecast, so treat it the same as the field being absent.
            if kind in ("height", "seconds") and value["value"] == 0:
                continue
            waves[field] = _friendly_wave_value(field, value)

        return live_result(SOURCE_FORECAST, {"periods": simplified_periods, "waves": waves})
    except (requests.RequestException, ValueError, KeyError) as exc:
        return failed_result(SOURCE_FORECAST, exc)


def get_active_alerts(lat, lon, user_agent, timeout=10):
    """Fetch active NWS alerts (High Surf, Small Craft, Rip Current, etc.) for a point.

    Returns the standard {live, source, data, fetched_at, error} dict, with
    data = a list of simplified alert dicts (empty list when none are active).
    """
    headers = {"User-Agent": user_agent, "Accept": "application/geo+json"}
    try:
        resp = requests.get(
            f"{BASE_URL}/alerts/active",
            params={"point": f"{lat},{lon}"},
            headers=headers,
            timeout=timeout,
        )
        resp.raise_for_status()
        features = resp.json().get("features", [])
        alerts = [
            {
                "event": f.get("properties", {}).get("event"),
                "headline": f.get("properties", {}).get("headline"),
                "severity": f.get("properties", {}).get("severity"),
                "effective": f.get("properties", {}).get("effective"),
                "expires": f.get("properties", {}).get("expires"),
            }
            for f in features
        ]
        return live_result(SOURCE_ALERTS, alerts)
    except (requests.RequestException, ValueError, KeyError) as exc:
        return failed_result(SOURCE_ALERTS, exc)
