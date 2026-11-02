from datetime import datetime

import routes.main as main_module
from models.reading import Reading
from services.external_common import failed_result
from services.reading_service import save_panel_snapshot


def add_manual(db, **overrides):
    fields = {
        "title": "Head high",
        "source": "crowdsurf-user",
        "external_id": "rincon:20261101T0730:head-high",
        "retrieved_at": datetime(2026, 11, 1, 15, 30),
        "break_id": "rincon",
        "kind": "observation",
        "data_json": {"wave_height_ft": 5.0},
    }
    fields.update(overrides)
    reading = Reading(**fields)
    db.session.add(reading)
    db.session.commit()
    return reading


# --- Read ---------------------------------------------------------------------

def test_readings_list_empty_state(client):
    response = client.get("/readings")
    assert response.status_code == 200
    assert b"No saved readings" in response.data


def test_readings_list_shows_records_and_filters(client, db):
    add_manual(db)
    response = client.get("/readings?break_id=rincon&kind=observation")
    assert response.status_code == 200
    assert b"Head high" in response.data
    assert b"No saved readings match" in client.get("/readings?break_id=south-jetty").data


def test_readings_list_bad_page_number_does_not_crash(client):
    assert client.get("/readings?page=abc").status_code == 200
    assert client.get("/readings?page=-5").status_code == 200


def test_reading_detail(client, db):
    reading = add_manual(db)
    response = client.get(f"/readings/{reading.id}")
    assert response.status_code == 200
    assert b"rincon:20261101T0730:head-high" in response.data


def test_unknown_reading_is_404(client):
    response = client.get("/readings/9999")
    assert response.status_code == 404
    assert b"doesn&#39;t exist" in response.data or b"doesn't exist" in response.data


# --- Create -------------------------------------------------------------------

def test_new_reading_form(client):
    assert client.get("/readings/new").status_code == 200


def test_create_valid_reading_redirects_to_detail(client, db):
    response = client.post("/readings/new", data={
        "break_id": "rincon", "title": "Clean lines", "kind": "observation", "wave_height_ft": "4",
    })
    assert response.status_code == 302
    assert db.session.query(Reading).count() == 1


def test_create_invalid_reading_shows_errors_and_saves_nothing(client, db):
    response = client.post("/readings/new", data={"break_id": "nope", "title": "", "wave_height_ft": "999"})
    assert response.status_code == 400
    assert b"Title is required." in response.data
    assert db.session.query(Reading).count() == 0


def test_create_duplicate_returns_409(client, db):
    form = {"break_id": "rincon", "title": "Same", "retrieved_at": "2026-11-01T07:30"}
    client.post("/readings/new", data=form)
    response = client.post("/readings/new", data=form)
    assert response.status_code == 409
    assert db.session.query(Reading).count() == 1


# --- Update -------------------------------------------------------------------

def test_edit_form_loads(client, db):
    reading = add_manual(db)
    response = client.get(f"/readings/{reading.id}/edit")
    assert response.status_code == 200
    assert b'value="Head high"' in response.data


def test_edit_valid(client, db):
    reading = add_manual(db)
    response = client.post(f"/readings/{reading.id}/edit", data={"title": "Overhead", "kind": "observation"})
    assert response.status_code == 302
    assert db.session.get(Reading, reading.id).title == "Overhead"


def test_edit_invalid_keeps_old_values(client, db):
    reading = add_manual(db)
    response = client.post(f"/readings/{reading.id}/edit", data={"title": "", "kind": "observation"})
    assert response.status_code == 400
    assert db.session.get(Reading, reading.id).title == "Head high"


def test_edit_unknown_reading_is_404(client):
    assert client.get("/readings/9999/edit").status_code == 404


# --- Delete -------------------------------------------------------------------

def test_delete_reading(client, db):
    reading = add_manual(db)
    response = client.post(f"/readings/{reading.id}/delete")
    assert response.status_code == 302
    assert db.session.query(Reading).count() == 0


def test_delete_requires_post(client, db):
    reading = add_manual(db)
    assert client.get(f"/readings/{reading.id}/delete").status_code == 405
    assert db.session.query(Reading).count() == 1


def test_delete_unknown_reading_is_404(client):
    assert client.post("/readings/9999/delete").status_code == 404


def test_csrf_token_required_when_enabled(app, client, db):
    app.config["WTF_CSRF_ENABLED"] = True
    reading = add_manual(db)
    response = client.post(f"/readings/{reading.id}/delete")
    assert response.status_code == 400
    assert db.session.query(Reading).count() == 1


# --- Break page: save, summarize, stored fallback ------------------------------

def test_save_snapshot_route(client, db, monkeypatch, fake_panel):
    monkeypatch.setattr(main_module, "build_break_panel", lambda *a, **k: fake_panel())
    response = client.post("/break/south-jetty/save", follow_redirects=True)
    assert response.status_code == 200
    assert b"Saved 11 new reading(s)" in response.data
    assert db.session.query(Reading).count() == 11


def test_save_snapshot_unknown_break_is_404(client):
    assert client.post("/break/not-a-break/save").status_code == 404


def test_summarize_without_api_key_shows_message(client):
    response = client.post("/break/south-jetty/summarize", follow_redirects=True)
    assert response.status_code == 200
    assert b"ANTHROPIC_API_KEY is not set" in response.data


def test_break_page_uses_stored_copy_when_source_is_down(client, db, monkeypatch, fake_panel, south_jetty):
    save_panel_snapshot(south_jetty, fake_panel())
    down = fake_panel(marine=failed_result("Open-Meteo Marine Weather API", "timeout"))
    monkeypatch.setattr(main_module, "build_break_panel", lambda *a, **k: down)

    response = client.get("/break/south-jetty")
    assert response.status_code == 200
    assert b"Showing the saved copy" in response.data
