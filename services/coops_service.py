"""NOAA CO-OPS Tides & Currents API -- no key, station-based.

Docs: https://api.tidesandcurrents.noaa.gov/api/prod/

Note: CO-OPS returns HTTP 200 with a body like
{"error": {"message": "..."}} when a station doesn't support a requested
product (e.g. many tide-only stations have no water-temperature sensor).
That has to be checked explicitly -- raise_for_status() alone won't catch it.
"""

import requests

from services.external_common import failed_result, live_result

SOURCE_TIDE_PREDICTIONS = "NOAA CO-OPS Tide Predictions"
SOURCE_TIDE_CURVE = "NOAA CO-OPS Tide Curve"
SOURCE_WATER_TEMP = "NOAA CO-OPS Water Temperature"

DATAGETTER_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

COMMON_PARAMS = {
    "datum": "MLLW",
    "units": "english",
    "time_zone": "lst_ldt",
    "format": "json",
}


def _get(params, timeout):
    """Shared GET + CO-OPS soft-error check. Raises ValueError on a soft error."""
    resp = requests.get(DATAGETTER_URL, params={**COMMON_PARAMS, **params}, timeout=timeout)
    resp.raise_for_status()
    body = resp.json()
    if "error" in body:
        raise ValueError(body["error"].get("message", "CO-OPS returned an error"))
    return body


def get_tide_predictions(station_id, timeout=10):
    """Fetch today's high/low tide predictions for a CO-OPS station.

    Returns the standard {live, source, data, fetched_at, error} dict, with
    data = a list of {time, type ("H"/"L"), height_ft}.
    """
    try:
        body = _get(
            {"station": station_id, "product": "predictions", "interval": "hilo", "date": "today"},
            timeout,
        )
        predictions = [
            {"time": p["t"], "type": p["type"], "height_ft": float(p["v"])}
            for p in body.get("predictions", [])
        ]
        return live_result(SOURCE_TIDE_PREDICTIONS, predictions)
    except (requests.RequestException, ValueError, KeyError) as exc:
        return failed_result(SOURCE_TIDE_PREDICTIONS, exc)


def get_tide_curve(station_id, timeout=10):
    """Fetch a smooth 30-minute-interval tide-height curve for today, for charting.

    Returns the standard {live, source, data, fetched_at, error} dict, with
    data = a list of {time, height_ft}.
    """
    try:
        body = _get(
            {"station": station_id, "product": "predictions", "interval": "30", "date": "today"},
            timeout,
        )
        curve = [{"time": p["t"], "height_ft": float(p["v"])} for p in body.get("predictions", [])]
        return live_result(SOURCE_TIDE_CURVE, curve)
    except (requests.RequestException, ValueError, KeyError) as exc:
        return failed_result(SOURCE_TIDE_CURVE, exc)


def get_water_temperature(station_id, timeout=10):
    """Fetch the latest observed water temperature for a station, if supported.

    Returns the standard {live, source, data, fetched_at, error} dict, with
    data = {"value_f": float, "time": str}. Not every station has a water
    temperature sensor -- that surfaces as live=False, not a crash.
    """
    try:
        body = _get(
            {"station": station_id, "product": "water_temperature", "date": "latest"}, timeout
        )
        reading = body.get("data", [])[0]
        return live_result(
            SOURCE_WATER_TEMP, {"value_f": float(reading["v"]), "time": reading["t"]}
        )
    except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
        return failed_result(SOURCE_WATER_TEMP, exc)
