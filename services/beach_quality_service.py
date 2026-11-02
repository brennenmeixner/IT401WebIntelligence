"""California State Water Resources Control Board: Beach Watch advisories.

Dataset: https://data.ca.gov/dataset/beach-water-quality-postings-and-closures
API: CKAN datastore_search on data.ca.gov (open data, no key).

Bacteria postings/closures matter to surfers: health agencies advise
staying out of the water near a posted station. The state republishes the
dataset roughly monthly, so this is recent *history*, not a real-time
status. The page labels it that way and shows the newest record's date.
"""

import json
import math

import requests

from services.external_common import failed_result, live_result

SOURCE = "CA Water Boards Beach Watch Advisories"

DATASTORE_URL = "https://data.ca.gov/api/3/action/datastore_search"
ADVISORIES_RESOURCE_ID = "d5cd6a23-829c-426d-a63e-689a55a3db9c"
DATASET_PAGE = "https://data.ca.gov/dataset/beach-water-quality-postings-and-closures"

REGION_TO_COUNTY = {
    "Ventura County": "Ventura",
    "Santa Barbara County": "Santa Barbara",
}

FIELDS = [
    "DateofAdvisory", "DateOpened", "AdvisoryType", "AdvisoryCause",
    "Station_Description", "Beach_Name", "Station_UpperLat", "Station_UpperLon",
]

RADIUS_KM = 5.0
MAX_RESULTS = 5


def distance_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two coordinates (haversine formula)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearby_advisories(records, lat, lon, radius_km=RADIUS_KM, limit=MAX_RESULTS):
    """Keep only advisories whose station is within radius_km of the break."""
    nearby = []
    for rec in records:
        s_lat, s_lon = rec.get("Station_UpperLat"), rec.get("Station_UpperLon")
        if s_lat is None or s_lon is None:
            continue
        km = distance_km(lat, lon, float(s_lat), float(s_lon))
        if km > radius_km:
            continue
        nearby.append(
            {
                "date": rec.get("DateofAdvisory"),
                "reopened": rec.get("DateOpened"),
                "type": rec.get("AdvisoryType"),
                "cause": rec.get("AdvisoryCause"),
                "station": rec.get("Station_Description") or rec.get("Beach_Name"),
                "distance_km": round(km, 1),
            }
        )
        if len(nearby) >= limit:
            break
    return nearby


def get_beach_advisories(region, lat, lon, timeout=10):
    """Fetch the county's most recent advisories and keep the ones near the break."""
    county = REGION_TO_COUNTY.get(region)
    if county is None:
        return failed_result(SOURCE, f"No Beach Watch county mapping for region '{region}'")

    params = {
        "resource_id": ADVISORIES_RESOURCE_ID,
        "filters": json.dumps({"County": county}),
        "sort": "DateofAdvisory desc",
        "limit": 200,
        "fields": ",".join(FIELDS),
    }
    try:
        resp = requests.get(DATASTORE_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise ValueError("data.ca.gov reported success=false")
        records = body["result"]["records"]
        return live_result(
            SOURCE,
            {
                "county": county,
                "latest_record_date": records[0].get("DateofAdvisory") if records else None,
                "advisories": nearby_advisories(records, lat, lon),
                "radius_km": RADIUS_KM,
            },
        )
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        return failed_result(SOURCE, exc)
