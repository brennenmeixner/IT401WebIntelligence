"""U.S. Naval Observatory Astronomical Applications API (no key).

https://aa.usno.navy.mil/data/api  (endpoint: /api/rstt/oneday)

Gives first light (civil twilight begin), sunrise, sunset, last light and
the moon phase. Surfers plan dawn-patrol and evening sessions around
these, and the moon phase drives how big the tide swings are.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from services.external_common import failed_result, live_result

SOURCE = "USNO Sun & Moon Data"

ONEDAY_URL = "https://aa.usno.navy.mil/api/rstt/oneday"
LOCAL_TZ = ZoneInfo("America/Los_Angeles")

# USNO phenomenon name -> our key
SUN_EVENTS = {
    "Begin Civil Twilight": "first_light",
    "Rise": "sunrise",
    "Set": "sunset",
    "End Civil Twilight": "last_light",
}


def _parse_oneday(body):
    props = body["properties"]["data"]
    sun = {}
    for event in props.get("sundata", []):
        key = SUN_EVENTS.get(event.get("phen"))
        if key:
            sun[key] = event.get("time")
    return {
        **sun,
        "moon_phase": props.get("curphase"),
        "moon_illumination": props.get("fracillum"),
    }


def get_sun_moon(lat, lon, timeout=10, now=None):
    """Fetch today's sun/moon times for a coordinate, in Pacific time.

    The USNO API needs the UTC offset as a number, so it is worked out
    from America/Los_Angeles for today (-8 in winter, -7 in summer).
    """
    now = now or datetime.now(LOCAL_TZ)
    offset_hours = now.utcoffset().total_seconds() / 3600
    params = {
        "date": now.strftime("%Y-%m-%d"),
        "coords": f"{lat},{lon}",
        "tz": int(offset_hours),
    }
    try:
        resp = requests.get(ONEDAY_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        data = _parse_oneday(resp.json())
        data["date"] = params["date"]
        return live_result(SOURCE, data)
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        return failed_result(SOURCE, exc)
