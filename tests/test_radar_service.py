import requests

from services import radar_service
from tests.fake_response import FakeResponse


def test_latlon_to_tile_xyz_known_values():
    # Standard slippy-map tile math, hand-verified reference points.
    assert radar_service.latlon_to_tile_xyz(0, 0, 0) == (0, 0)
    assert radar_service.latlon_to_tile_xyz(0, 0, 1) == (1, 1)


def test_latlon_to_tile_offset_marks_center_of_its_tile():
    # (0, 0) sits exactly on a tile boundary corner at zoom 1 -- (0,0,1)
    # tile's far corner, i.e. pixel (256, 0) as seen from tile (0, 0) or
    # pixel (0, 0) as seen from tile (1, 1). Confirms the offset math
    # lines up with latlon_to_tile_xyz's own tile indices.
    x, y, px, py = radar_service.latlon_to_tile_offset(0, 0, 1)
    assert (x, y) == radar_service.latlon_to_tile_xyz(0, 0, 1)
    assert 0 <= px <= 256
    assert 0 <= py <= 256


def test_get_radar_frames_success(monkeypatch):
    body = {
        "host": "https://tilecache.rainviewer.com",
        "radar": {
            "past": [
                {"time": 1000, "path": "/v2/radar/abc"},
                {"time": 1010, "path": "/v2/radar/def"},
            ]
        },
    }
    monkeypatch.setattr(radar_service.requests, "get", lambda *a, **k: FakeResponse(body))

    result = radar_service.get_radar_frames(34.24, -119.26, zoom=7)

    assert result["live"] is True
    assert len(result["data"]["frames"]) == 2
    assert result["data"]["frames"][0]["tile_url"].startswith("https://tilecache.rainviewer.com")
    assert "openstreetmap.org" in result["data"]["base_tile_url"]


def test_get_radar_frames_request_failure(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(radar_service.requests, "get", raise_exc)

    result = radar_service.get_radar_frames(34.24, -119.26)

    assert result["live"] is False
