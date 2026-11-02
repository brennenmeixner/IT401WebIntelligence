"""Orchestrator: assembles one break's full data panel from every source.

This is the only external-data function routes/main.py calls directly.
Every sub-call is wrapped in its own try/except *in addition to* each
service's internal error handling -- belt-and-suspenders, so a genuinely
unexpected exception in one source can never take down the whole page.
Every value in the returned dict is a standard {live, source, data,
fetched_at, error} result; this function itself never raises, even if
every single source is unreachable.

The sources are fetched in parallel (a small thread pool) because each one
mostly waits on the network: 14 calls one after another took ~8 seconds,
in parallel the page waits only about as long as the slowest source.
"""

from concurrent.futures import ThreadPoolExecutor

from services.beach_quality_service import get_beach_advisories
from services.buoy_scraper_service import scrape_latest_observation
from services.coops_service import get_tide_curve, get_tide_predictions, get_water_temperature
from services.external_common import failed_result
from services.ndbc_realtime_service import get_realtime_observations
from services.nws_service import get_active_alerts, get_gridpoint_forecast
from services.openmeteo_service import get_marine_forecast, get_weather_forecast
from services.radar_service import get_radar_frames
from services.rapidapi_marine_service import get_marine_second_opinion
from services.spc_service import get_convective_outlook
from services.usno_service import get_sun_moon


def _safe(source_label, fn, *args, **kwargs):
    """Call an external-data function; never let it escape as a raw exception."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 -- last-resort guard, see module docstring
        return failed_result(source_label, exc)


def build_break_panel(break_record, nws_user_agent, timeout=10, rapidapi_key=None):
    """Fetch every external data source for one break and assemble a template context.

    break_record must already carry latitude/longitude/nws_office/
    nws_grid_x/nws_grid_y/ndbc_station/coops_station (see data/breaks.json).
    """
    lat = break_record["latitude"]
    lon = break_record["longitude"]

    with ThreadPoolExecutor(max_workers=8) as pool:

        def run(source_label, fn, *args):
            # Start the call in the background; collect the result below.
            return pool.submit(_safe, source_label, fn, *args)

        futures = {
            "marine": run("Open-Meteo Marine Weather API", get_marine_forecast, lat, lon, timeout),
            "weather": run(
                "Open-Meteo Weather Forecast API", get_weather_forecast, lat, lon, timeout
            ),
            "nws_forecast": run(
                "NOAA NWS Gridpoint Forecast",
                get_gridpoint_forecast,
                break_record["nws_office"],
                break_record["nws_grid_x"],
                break_record["nws_grid_y"],
                nws_user_agent,
                timeout,
            ),
            "nws_alerts": run(
                "NOAA NWS Active Alerts", get_active_alerts, lat, lon, nws_user_agent, timeout
            ),
            "tide_predictions": run(
                "NOAA CO-OPS Tide Predictions",
                get_tide_predictions,
                break_record["coops_station"],
                timeout,
            ),
            "tide_curve": run(
                "NOAA CO-OPS Tide Curve", get_tide_curve, break_record["coops_station"], timeout
            ),
            "water_temp": run(
                "NOAA CO-OPS Water Temperature",
                get_water_temperature,
                break_record["coops_station"],
                timeout,
            ),
            "spc_outlook": run(
                "NOAA SPC Day-1 Convective Outlook", get_convective_outlook, lat, lon, 1, timeout
            ),
            "radar": run("RainViewer Radar", get_radar_frames, lat, lon, 7, timeout),
            "buoy_reading": run(
                "NOAA NDBC Buoy Observation (scraped)",
                scrape_latest_observation,
                break_record["ndbc_station"],
                timeout,
            ),
            "buoy_history": run(
                "NOAA NDBC Realtime Observations",
                get_realtime_observations,
                break_record["ndbc_station"],
                timeout,
            ),
            "rapid_marine": run(
                "WeatherAPI.com Marine (via RapidAPI)",
                get_marine_second_opinion,
                lat,
                lon,
                rapidapi_key,
                timeout,
            ),
            "sun_moon": run("USNO Sun & Moon Data", get_sun_moon, lat, lon, timeout),
            "beach_quality": run(
                "CA Water Boards Beach Watch Advisories",
                get_beach_advisories,
                break_record.get("region"),
                lat,
                lon,
                timeout,
            ),
        }

    panel = {key: future.result() for key, future in futures.items()}
    panel["break"] = break_record
    return panel
