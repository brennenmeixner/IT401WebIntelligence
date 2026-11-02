from config import Config
from services.breaks_service import filter_breaks, find_break, load_breaks

# The `client` fixture now lives in tests/conftest.py (TestConfig + in-memory DB).


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200


def test_explore(client):
    response = client.get("/explore")
    assert response.status_code == 200


def test_explore_with_filters(client):
    response = client.get("/explore?q=rincon&region=Santa+Barbara+County&wind=Glassy")
    assert response.status_code == 200
    assert b"Rincon" in response.data


def test_explore_no_matches_shows_empty_state(client):
    response = client.get("/explore?q=nonexistent-break-xyz")
    assert response.status_code == 200
    assert b"Flat. Nothing here." in response.data


def test_rewards(client):
    response = client.get("/rewards")
    assert response.status_code == 200


def test_filter_breaks_no_match_returns_empty_list():
    breaks = load_breaks(Config.DATA_DIR)
    assert filter_breaks(breaks, q="not-a-real-break") == []


def test_find_break_returns_matching_record():
    breaks = load_breaks(Config.DATA_DIR)
    result = find_break(breaks, "rincon")
    assert result is not None
    assert result["name"] == "Rincon"


def test_find_break_returns_none_for_unknown_id():
    breaks = load_breaks(Config.DATA_DIR)
    assert find_break(breaks, "not-a-real-id") is None


def test_explore_has_view_details_link(client):
    response = client.get("/explore")
    assert b"/break/" in response.data


def test_break_detail_known_id(client, monkeypatch, fake_panel):
    import routes.main as main_module

    monkeypatch.setattr(main_module, "build_break_panel", lambda *a, **k: fake_panel())

    response = client.get("/break/south-jetty")
    assert response.status_code == 200
    assert b"South Jetty" in response.data
    assert b"Save this snapshot" in response.data


def test_break_detail_unknown_id(client):
    response = client.get("/break/not-a-real-id")
    assert response.status_code == 404
    assert b"not found" in response.data.lower()
