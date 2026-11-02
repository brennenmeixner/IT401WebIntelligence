"""One place that describes every data source the app can persist.

Each entry maps a key in the break panel (see forecast_service) to:
- slug: the short, stable value stored in readings.source
- label: the human-readable name shown in the UI
- kind: "forecast" or "observation"
- url: a function(break_record) -> the exact URL the data came from
       (stored in readings.source_url for provenance)

Radar is deliberately not listed: it is a set of image tiles, not values,
so a saved copy wouldn't be useful.
"""

from models.reading import KIND_FORECAST, KIND_NOTE, KIND_OBSERVATION, KIND_SUMMARY


def _openmeteo_marine(b):
    return f"https://marine-api.open-meteo.com/v1/marine?latitude={b['latitude']}&longitude={b['longitude']}"


def _openmeteo_weather(b):
    return f"https://api.open-meteo.com/v1/forecast?latitude={b['latitude']}&longitude={b['longitude']}"


def _nws_forecast(b):
    return f"https://api.weather.gov/gridpoints/{b['nws_office']}/{b['nws_grid_x']},{b['nws_grid_y']}/forecast"


def _nws_alerts(b):
    return f"https://api.weather.gov/alerts/active?point={b['latitude']},{b['longitude']}"


def _coops(product):
    def build(b):
        return (
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
            f"?station={b['coops_station']}&product={product}"
        )
    return build


def _spc(b):
    return f"https://mesonet.agron.iastate.edu/json/spcoutlook.py?lat={b['latitude']}&lon={b['longitude']}&day=1"


def _ndbc_page(b):
    return f"https://www.ndbc.noaa.gov/station_page.php?station={b['ndbc_station']}"


def _ndbc_feed(b):
    return f"https://www.ndbc.noaa.gov/data/realtime2/{b['ndbc_station']}.txt"


def _rapidapi(b):
    # The listing page, not the API call: the call needs a secret header.
    return "https://rapidapi.com/weatherapi/api/weatherapi-com"


def _usno(b):
    return f"https://aa.usno.navy.mil/api/rstt/oneday?coords={b['latitude']},{b['longitude']}"


def _beach(b):
    return "https://data.ca.gov/dataset/beach-water-quality-postings-and-closures"


PANEL_SOURCES = {
    "marine": {"slug": "open-meteo-marine", "label": "Open-Meteo Marine", "kind": KIND_FORECAST, "url": _openmeteo_marine},
    "weather": {"slug": "open-meteo-weather", "label": "Open-Meteo Weather", "kind": KIND_FORECAST, "url": _openmeteo_weather},
    "nws_forecast": {"slug": "noaa-nws-forecast", "label": "NOAA NWS Forecast", "kind": KIND_FORECAST, "url": _nws_forecast},
    "nws_alerts": {"slug": "noaa-nws-alerts", "label": "NOAA NWS Alerts", "kind": KIND_OBSERVATION, "url": _nws_alerts},
    "tide_predictions": {"slug": "noaa-coops-tides", "label": "NOAA CO-OPS Tide Predictions", "kind": KIND_FORECAST, "url": _coops("predictions")},
    "tide_curve": {"slug": "noaa-coops-tide-curve", "label": "NOAA CO-OPS Tide Curve", "kind": KIND_FORECAST, "url": _coops("predictions")},
    "water_temp": {"slug": "noaa-coops-water-temp", "label": "NOAA CO-OPS Water Temperature", "kind": KIND_OBSERVATION, "url": _coops("water_temperature")},
    "spc_outlook": {"slug": "noaa-spc-outlook", "label": "NOAA SPC Convective Outlook", "kind": KIND_FORECAST, "url": _spc},
    "buoy_reading": {"slug": "noaa-ndbc-scrape", "label": "NOAA NDBC Buoy Page (scraped)", "kind": KIND_OBSERVATION, "url": _ndbc_page},
    "buoy_history": {"slug": "noaa-ndbc-realtime", "label": "NOAA NDBC Realtime Feed", "kind": KIND_OBSERVATION, "url": _ndbc_feed},
    "rapid_marine": {"slug": "rapidapi-weatherapi-marine", "label": "WeatherAPI.com Marine (RapidAPI)", "kind": KIND_FORECAST, "url": _rapidapi},
    "sun_moon": {"slug": "usno-sun-moon", "label": "USNO Sun & Moon", "kind": KIND_FORECAST, "url": _usno},
    "beach_quality": {"slug": "ca-beach-watch", "label": "CA Beach Watch Advisories", "kind": KIND_OBSERVATION, "url": _beach},
}

# Sources that aren't panel results.
MANUAL_SOURCE = {"slug": "crowdsurf-user", "label": "Crowdsurf user entry", "kind": KIND_NOTE}
AI_SOURCE = {"slug": "anthropic-claude", "label": "Claude AI summary", "kind": KIND_SUMMARY}

SOURCE_LABELS = {entry["slug"]: entry["label"] for entry in PANEL_SOURCES.values()}
SOURCE_LABELS[MANUAL_SOURCE["slug"]] = MANUAL_SOURCE["label"]
SOURCE_LABELS[AI_SOURCE["slug"]] = AI_SOURCE["label"]

ALLOWED_SOURCES = tuple(SOURCE_LABELS)

# Panel key looked up by slug (used for the "show stored copy" fallback).
PANEL_KEY_BY_SLUG = {entry["slug"]: key for key, entry in PANEL_SOURCES.items()}
