import json
import os

WIND_COLORS = {
    "Offshore": "#1f8a3c",
    "Onshore": "#1f6fd0",
    "Glassy": "#111111",
    "Cross-shore": "#b07d0a",
}

ALL_REGIONS = "All regions"
ANY_WIND = "Any wind"


def load_breaks(data_dir):
    """Read the list of surf breaks from data/breaks.json, or [] if missing/invalid."""
    path = os.path.join(data_dir, "breaks.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def filter_breaks(breaks, q=None, region=None, wind=None):
    """Filter breaks by name/location substring, region, and wind condition.

    Missing or blank filters are treated as "no constraint". Never raises —
    breaks missing expected keys are skipped via .get() defaults.
    """
    needle = (q or "").strip().lower()
    region = region or ALL_REGIONS
    wind = wind or ANY_WIND

    results = []
    for b in breaks:
        name = b.get("name", "")
        location = b.get("location", "")
        b_region = b.get("region", "")
        b_wind = b.get("forecast", {}).get("wind", "")

        matches_q = not needle or needle in name.lower() or needle in location.lower()
        matches_region = region == ALL_REGIONS or region == b_region
        matches_wind = wind == ANY_WIND or wind == b_wind

        if matches_q and matches_region and matches_wind:
            results.append({**b, "wind_color": WIND_COLORS.get(b_wind, "#111111")})

    return results
