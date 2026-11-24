"""NOAA NDBC realtime2 standard meteorological feed (no key).

https://www.ndbc.noaa.gov/data/realtime2/<station>.txt

The A2 scraper reads only the *current* reading off the HTML station page.
This plain-text feed has the last 45 days of observations, so it gives an
observed trend (is the swell building or dropping?) to compare against the
forecast. Values of "MM" mean "missing" and become None.
"""

import requests

from services.external_common import failed_result, live_result

SOURCE = "NOAA NDBC Realtime Observations"

FEED_URL = "https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt"
REQUEST_HEADERS = {"User-Agent": "crowdsurf-it401-student-project (educational use)"}

ROWS_TO_KEEP = 24

M_TO_FT = 3.28084
MS_TO_KT = 1.94384


def _num(value):
    if value in (None, "MM"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _c_to_f(c):
    return None if c is None else round(c * 9 / 5 + 32, 1)


def _scaled(value, factor):
    return None if value is None else round(value * factor, 1)


def parse_realtime_text(text, max_rows=ROWS_TO_KEEP):
    """Parse the whitespace-separated feed into a list of dicts, newest first.

    Only rows that report a wave height are kept, since wave height is
    what the app compares against the forecast.
    """
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("#"):
        raise ValueError("Unexpected NDBC feed format")

    columns = lines[0].lstrip("#").split()
    rows = []
    for line in lines:
        if line.startswith("#"):
            continue
        values = dict(zip(columns, line.split()))
        wave_m = _num(values.get("WVHT"))
        if wave_m is None:
            continue
        rows.append(
            {
                "time_utc": "{}-{}-{}T{}:{}Z".format(
                    values.get("YY"), values.get("MM"), values.get("DD"),
                    values.get("hh"), values.get("mm"),
                ),
                "wave_height_ft": _scaled(wave_m, M_TO_FT),
                "dominant_period_s": _num(values.get("DPD")),
                "average_period_s": _num(values.get("APD")),
                "wave_direction_deg": _num(values.get("MWD")),
                "wind_speed_kt": _scaled(_num(values.get("WSPD")), MS_TO_KT),
                "water_temp_f": _c_to_f(_num(values.get("WTMP"))),
            }
        )
        if len(rows) >= max_rows:
            break
    return rows


def get_realtime_observations(station_id, timeout=10):
    """Fetch recent observed wave/wind rows for one NDBC station.

    Returns the standard result dict with data = {"station", "rows",
    "latest"}. An empty rows list is still live=True (the station is up
    but reported no waves).
    """
    url = FEED_URL.format(station_id=station_id)
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
        resp.raise_for_status()
        rows = parse_realtime_text(resp.text)
        return live_result(
            SOURCE,
            {"station": station_id, "rows": rows, "latest": rows[0] if rows else None},
        )
    except (requests.RequestException, ValueError) as exc:
        return failed_result(SOURCE, exc)
