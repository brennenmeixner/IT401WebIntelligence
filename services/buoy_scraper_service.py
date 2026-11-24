"""Web scrape: NOAA NDBC buoy station observation page.

https://www.ndbc.noaa.gov/station_page.php?station=<id>

This is the "ground truth" source: a real instrument reading, scraped and
shown next to the Open-Meteo/NWS *forecast* numbers for the same break.
Confirmed against https://www.ndbc.noaa.gov/robots.txt (2026-09-20): the
only disallowed user-agents are specific bots (008, SemrushBot,
SemrushBot-SA); a normal descriptive User-Agent on station_page.php is
not restricted.

The page has no id/class hooks to select on, so fields are matched by
their label text (e.g. "Significant Wave Height (WVHT):") and the value
is read from the next table cell.
"""

import re

import requests
from bs4 import BeautifulSoup

from services.external_common import failed_result, live_result

SOURCE = "NOAA NDBC Buoy Observation (scraped)"

STATION_PAGE_URL = "https://www.ndbc.noaa.gov/station_page.php?station={station_id}"

REQUEST_HEADERS = {"User-Agent": "crowdsurf-it401-student-project (educational use)"}

# Label marker -> result key. Order doesn't matter; each field is matched
# and extracted independently so one missing/renamed label only omits
# that one key rather than failing the whole scrape.
FIELD_LABELS = {
    "(WVHT)": "wave_height_ft",
    "(DPD)": "dominant_period_s",
    "(WSPD)": "wind_speed_kt",
    "(WDIR)": "wind_direction",
    "(WTMP)": "water_temp_f",
    "(PRES)": "pressure_in",
}

NUMBER_RE = re.compile(r"-?\d+\.?\d*")


def _extract_number(text):
    match = NUMBER_RE.search(text)
    return float(match.group()) if match else None


def _parse_observation(html):
    """Pull known fields out of the station page HTML. Never raises."""
    soup = BeautifulSoup(html, "html.parser")
    data = {}
    for label_cell in soup.find_all("td"):
        label_text = label_cell.get_text()
        for marker, key in FIELD_LABELS.items():
            if marker not in label_text or key in data:
                continue
            value_cell = label_cell.find_next_sibling("td")
            if value_cell is None:
                continue
            value_text = value_cell.get_text(strip=True)
            if key == "wind_direction":
                data[key] = value_text
            else:
                number = _extract_number(value_text)
                if number is not None:
                    data[key] = number
    return data


def scrape_latest_observation(station_id, timeout=10):
    """Scrape the current-conditions table on an NDBC station page.

    Returns the standard {live, source, data, fetched_at, error} dict.
    live=False only when the request itself fails; a page that loads but
    matches zero fields still returns live=True with an empty dict, since
    that's a legitimate "no sensor data published here" observation
    (e.g. a wind-only C-MAN station), not a scraping error.
    """
    url = STATION_PAGE_URL.format(station_id=station_id)
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return failed_result(SOURCE, exc)

    try:
        data = _parse_observation(resp.text)
        return live_result(SOURCE, data)
    except (AttributeError, TypeError, ValueError) as exc:
        return failed_result(SOURCE, exc)
