"""RainViewer Weather Maps API -- no key, no signup.

Docs: https://www.rainviewer.com/api.html

Provides the "visual data" requirement: radar tile images (not just
numbers) stacked over a plain OpenStreetMap base tile at the same
z/x/y, using standard slippy-map tile math -- no JS mapping library
required for a small fixed-frame view.

RainViewer's free terms require visible attribution in the UI:
"Weather data by RainViewer" linking to https://www.rainviewer.com/
(added in templates/break_detail.html, not here).
"""

import math

import requests

from services.external_common import failed_result, live_result

SOURCE = "RainViewer Radar"

INDEX_URL = "https://api.rainviewer.com/public/weather-maps.json"
TILE_SIZE = 256
COLOR_SCHEME = 2  # "Universal Blue" -- readable on both light and dark UI
SMOOTH = 1
SNOW = 1
FRAME_COUNT = 3

# RainViewer's radar tiles only render real data up to zoom 7 -- confirmed
# by probing their tile server directly (zoom 8+ silently returns a fixed
# "Zoom Level Not Supported" placeholder image instead of an error). A
# zoom-7 tile still covers ~150+ miles, so on its own the break isn't
# visually "localized" -- the fix is the marker pin below (see
# latlon_to_tile_offset), which pinpoints the break's exact pixel position
# within that tile rather than trying to zoom in past what RainViewer supports.
DEFAULT_ZOOM = 7


def latlon_to_tile_offset(lat, lon, zoom):
    """Convert a coordinate + zoom level to its tile indices and exact pixel
    position within that tile (for placing a marker on the break itself).

    Pure function, no network call -- exact input/output pairs are unit-testable.
    Returns (x_tile, y_tile, pixel_x, pixel_y).
    """
    lat_rad = math.radians(lat)
    n = 2**zoom
    x_float = (lon + 180.0) / 360.0 * n
    y_float = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    x_tile = int(x_float)
    y_tile = int(y_float)
    pixel_x = (x_float - x_tile) * TILE_SIZE
    pixel_y = (y_float - y_tile) * TILE_SIZE
    return x_tile, y_tile, pixel_x, pixel_y


def latlon_to_tile_xyz(lat, lon, zoom):
    """Convert a coordinate + zoom level to standard slippy-map (x, y) tile indices."""
    x, y, _px, _py = latlon_to_tile_offset(lat, lon, zoom)
    return x, y


def get_radar_frames(lat, lon, zoom=DEFAULT_ZOOM, timeout=10):
    """Fetch the last few radar frames as tile image URLs for a coordinate.

    Returns the standard {live, source, data, fetched_at, error} dict, with
    data = {"frames": [...], "base_tile_url": str, "marker_x": float,
    "marker_y": float} -- marker_x/y are the break's exact pixel position
    within the tile, for overlaying a pin so the break's location reads as
    localized rather than "somewhere in this tile."
    """
    try:
        resp = requests.get(INDEX_URL, timeout=timeout)
        resp.raise_for_status()
        body = resp.json()
        host = body["host"]
        past_frames = body.get("radar", {}).get("past", [])[-FRAME_COUNT:]

        x, y, marker_x, marker_y = latlon_to_tile_offset(lat, lon, zoom)
        frames = [
            {
                "time": frame["time"],
                "tile_url": (
                    f"{host}{frame['path']}/{TILE_SIZE}/{zoom}/{x}/{y}/"
                    f"{COLOR_SCHEME}/{SMOOTH}_{SNOW}.png"
                ),
            }
            for frame in past_frames
        ]
        base_tile_url = f"https://tile.openstreetmap.org/{zoom}/{x}/{y}.png"

        return live_result(
            SOURCE,
            {
                "frames": frames,
                "base_tile_url": base_tile_url,
                "marker_x": round(marker_x, 1),
                "marker_y": round(marker_y, 1),
            },
        )
    except (requests.RequestException, ValueError, KeyError) as exc:
        return failed_result(SOURCE, exc)
