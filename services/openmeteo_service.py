"""Open-Meteo Marine + Weather Forecast APIs (no key, no signup required).

Docs: https://open-meteo.com/en/docs/marine-weather-api
      https://open-meteo.com/en/docs
"""

import requests

from services.external_common import failed_result, live_result

SOURCE_MARINE = "Open-Meteo Marine Weather API"
SOURCE_WEATHER = "Open-Meteo Weather Forecast API"

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

MARINE_HOURLY_FIELDS = (
    "wave_height,wave_direction,wave_period,"
    "wind_wave_height,wind_wave_direction,wind_wave_period,"
    "swell_wave_height,swell_wave_direction,swell_wave_period,swell_wave_peak_period,"
    "sea_surface_temperature"
)
WEATHER_HOURLY_FIELDS = (
    "temperature_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,"
    "precipitation_probability,cloud_cover,uv_index"
)


def get_marine_forecast(lat, lon, timeout=10):
    """Fetch hourly swell/wave/wind-wave/sea-temp data for a coordinate.

    Returns the standard {live, source, data, fetched_at, error} dict.
    live=False/data=None on any request failure or unexpected response shape.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": MARINE_HOURLY_FIELDS,
        "timezone": "auto",
        "forecast_days": 3,
    }
    try:
        resp = requests.get(MARINE_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        body = resp.json()
        return live_result(
            SOURCE_MARINE,
            {"hourly": body["hourly"], "hourly_units": body.get("hourly_units", {})},
        )
    except (requests.RequestException, ValueError, KeyError) as exc:
        return failed_result(SOURCE_MARINE, exc)


def get_weather_forecast(lat, lon, timeout=10):
    """Fetch hourly temp/wind/precip/cloud/UV data for a coordinate.

    Returns the standard {live, source, data, fetched_at, error} dict.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": WEATHER_HOURLY_FIELDS,
        "timezone": "auto",
        "forecast_days": 3,
    }
    try:
        resp = requests.get(WEATHER_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        body = resp.json()
        return live_result(
            SOURCE_WEATHER,
            {"hourly": body["hourly"], "hourly_units": body.get("hourly_units", {})},
        )
    except (requests.RequestException, ValueError, KeyError) as exc:
        return failed_result(SOURCE_WEATHER, exc)
