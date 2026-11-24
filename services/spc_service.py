"""NOAA SPC Day-1 Convective Outlook -- beach/lightning-safety panel.

Queried through the Iowa State Mesonet point-query proxy
(https://mesonet.agron.iastate.edu/json/spcoutlook.py), which performs the
point-in-polygon test against NOAA SPC's own published outlook so this
project doesn't have to implement polygon geometry itself. The data origin
is still NOAA SPC; the delivery mechanism is a third-party academic mirror
-- documented in the README's Ethical Considerations / Known Limitations.

The endpoint returns every historical outlook issuance where this point
was inside a category >= the requested threshold, most recent first -- not
a single "today's risk" value. This service takes the most recent entry
and treats it as "no current elevated risk" if its expiration has already
passed.
"""

from datetime import datetime, timezone

import requests

from services.external_common import failed_result, live_result

SOURCE = "NOAA SPC Day-1 Convective Outlook"

URL = "https://mesonet.agron.iastate.edu/json/spcoutlook.py"

CATEGORY_LABELS = {
    "TSTM": "General Thunderstorms",
    "MRGL": "Marginal",
    "SLGT": "Slight",
    "ENH": "Enhanced",
    "MDT": "Moderate",
    "HIGH": "High",
}


def _parse_utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def get_convective_outlook(lat, lon, day=1, timeout=10):
    """Fetch the most recent Day-N severe thunderstorm risk category for a point.

    Returns the standard {live, source, data, fetched_at, error} dict, with
    data = {"active": bool, "threshold": str|None, "label": str|None,
    "expires": str|None}. "active" is False (with threshold/label None)
    when no current outlook is in effect above the marginal threshold.
    """
    try:
        resp = requests.get(
            URL, params={"lat": lat, "lon": lon, "day": day, "cat": "categorical"}, timeout=timeout
        )
        resp.raise_for_status()
        outlooks = resp.json().get("outlooks", [])

        if not outlooks:
            return live_result(SOURCE, {"active": False, "threshold": None, "label": None, "expires": None})

        latest = outlooks[0]
        expires = latest.get("utc_expire")
        is_active = bool(expires) and _parse_utc(expires) > datetime.now(timezone.utc)

        if not is_active:
            return live_result(SOURCE, {"active": False, "threshold": None, "label": None, "expires": None})

        threshold = latest.get("threshold")
        return live_result(
            SOURCE,
            {
                "active": True,
                "threshold": threshold,
                "label": CATEGORY_LABELS.get(threshold, threshold),
                "expires": expires,
            },
        )
    except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
        return failed_result(SOURCE, exc)
