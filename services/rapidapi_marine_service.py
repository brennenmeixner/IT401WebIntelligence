"""RapidAPI: WeatherAPI.com Marine Weather API (keyed).

Listing: https://rapidapi.com/weatherapi/api/weatherapi-com
Endpoint: GET https://weatherapi-com.p.rapidapi.com/marine.json

Used as a "second opinion" forecast next to Open-Meteo: an independent
model's swell height, period and direction, plus its own tide table. It is
the only keyed source in the app. The key comes from RAPIDAPI_KEY in .env
and is sent in a request header, so it never appears in a URL or log line.
"""

import requests

from services.external_common import failed_result, live_result

SOURCE = "WeatherAPI.com Marine (via RapidAPI)"

RAPIDAPI_HOST = "weatherapi-com.p.rapidapi.com"
MARINE_URL = f"https://{RAPIDAPI_HOST}/marine.json"

HOURS_TO_KEEP = 48


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_marine(body):
    """Flatten WeatherAPI's nested forecastday/hour structure. Never raises
    on missing optional fields; raises KeyError/TypeError only if the core
    'forecast' block is missing entirely."""
    days = body["forecast"]["forecastday"]

    hours = []
    tides = []
    for day in days:
        for h in day.get("hour", []):
            hours.append(
                {
                    "time": h.get("time"),
                    "sig_wave_height_m": _to_float(h.get("sig_ht_mt")),
                    "swell_height_ft": _to_float(h.get("swell_ht_ft")),
                    "swell_period_s": _to_float(h.get("swell_period_secs")),
                    "swell_direction": h.get("swell_dir_16_point"),
                    "wind_kph": _to_float(h.get("wind_kph")),
                    "wind_direction": h.get("wind_dir"),
                    "water_temp_f": _to_float(h.get("water_temp_f")),
                }
            )
        for tide_block in day.get("day", {}).get("tides", []):
            for t in tide_block.get("tide", []):
                tides.append(
                    {
                        "time": t.get("tide_time"),
                        "type": t.get("tide_type"),
                        "height_m": _to_float(t.get("tide_height_mt")),
                    }
                )

    location = body.get("location", {})
    return {
        "location_name": location.get("name"),
        "hours": hours[:HOURS_TO_KEEP],
        "tides": tides,
    }


def get_marine_second_opinion(lat, lon, api_key, timeout=10):
    """Fetch a 2-day marine forecast + tides from WeatherAPI.com via RapidAPI.

    Returns the standard {live, source, data, fetched_at, error} dict.
    Without a key it returns live=False with a clear message instead of
    calling the API, so the page still renders.
    """
    if not api_key:
        return failed_result(SOURCE, "RAPIDAPI_KEY is not set in .env")

    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": RAPIDAPI_HOST}
    params = {"q": f"{lat},{lon}", "days": 2, "tides": "yes"}
    try:
        resp = requests.get(MARINE_URL, headers=headers, params=params, timeout=timeout)
        resp.raise_for_status()
        return live_result(SOURCE, _parse_marine(resp.json()))
    except requests.HTTPError as exc:
        # Don't echo the response body: it can repeat request details.
        status = exc.response.status_code if exc.response is not None else "?"
        return failed_result(SOURCE, f"RapidAPI returned HTTP {status}")
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        return failed_result(SOURCE, exc)
