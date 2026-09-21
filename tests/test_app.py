import pytest

from app import create_app
from config import Config
from services.breaks_service import filter_breaks, load_breaks


@pytest.fixture
def client():
    app = create_app("development")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


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
