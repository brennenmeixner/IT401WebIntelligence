from datetime import datetime

from sqlalchemy.exc import OperationalError

import routes.search as search_routes
from models.reading import Reading
from models.search_event import SearchEvent
from services import search_service


def add(db, title, description=None, break_id="rincon", day=1):
    reading = Reading(title=title, description=description, source="crowdsurf-user", kind="note",
                      external_id=f"{break_id}:{title}:{day}", retrieved_at=datetime(2026, 11, day, 12),
                      break_id=break_id)
    db.session.add(reading)
    db.session.commit()
    return reading


def test_before_searching_state(client, db):
    response = client.get("/search")
    assert response.status_code == 200
    assert b"Enter a keyword to begin." in response.data
    assert db.session.query(SearchEvent).count() == 0  # empty visits aren't logged


def test_results_keep_query_and_filters_in_the_form(client, db):
    add(db, "Rincon swell", description=None)
    response = client.get("/search?q=Rincon+swell&kind=note&sort=title")
    html = response.data.decode()
    assert "1 result found for “Rincon swell.”" in html
    assert 'value="Rincon swell"' in html
    assert '<option value="note" selected>' in html
    assert '<option value="title" selected>' in html
    assert "No description." in html  # missing description gets a placeholder
    assert "Kind: note" in html  # removable chip


def test_no_results_state(client, db):
    response = client.get("/search?q=tsunami+warning")
    assert b"No matching records were found. Try a broader term or remove a filter." in response.data
    assert db.session.query(SearchEvent).one().no_result


def test_bad_values_never_crash(client, db):
    add(db, "Swell")
    response = client.get("/search?q=swell&page=abc&source=nope&date_from=yesterday&sort=x")
    assert response.status_code == 200
    html = response.data.decode()
    assert "isn&#39;t a page number" in html
    assert "Ignored unknown filter value" in html
    assert "dates must look like" in html


def test_database_down_shows_friendly_error(client, monkeypatch):
    def boom(*args, **kwargs):
        raise OperationalError("SELECT", {}, Exception("connection refused"))
    monkeypatch.setattr(search_service.db, "paginate", boom)
    response = client.get("/search?q=swell")
    assert response.status_code == 503
    assert b"Search is temporarily unavailable." in response.data
    assert b"Traceback" not in response.data


def test_pagination_links_keep_state_and_do_not_log_again(client, db):
    for day in range(1, 13):
        add(db, f"Swell {day}", day=day)
    page1 = client.get("/search?q=swell&kind=note").data.decode()
    assert "Showing 1 to 10" in page1
    event = db.session.query(SearchEvent).one()
    assert f"se={event.id}" in page1 and "kind=note" in page1 and "page=2" in page1

    page2 = client.get(f"/search?q=swell&kind=note&sort=relevance&page=2&se={event.id}").data.decode()
    assert "Showing 11 to 12" in page2
    assert db.session.query(SearchEvent).count() == 1  # a page turn isn't a new search


def test_opening_a_result_records_the_selection(client, db):
    reading = add(db, "Swell")
    client.get("/search?q=swell")
    event = db.session.query(SearchEvent).one()
    assert client.get(f"/readings/{reading.id}?se={event.id}&rank=1").status_code == 200
    db.session.refresh(event)
    assert (event.selected_reading_id, event.selected_rank) == (reading.id, 1)


def test_bogus_selection_params_are_ignored(client, db):
    reading = add(db, "Swell")
    assert client.get(f"/readings/{reading.id}?se=999&rank=abc").status_code == 200


def test_search_history_page(client, db):
    add(db, "Swell")
    client.get("/search?q=swell")
    response = client.get("/search/history")
    assert response.status_code == 200
    assert b"1 search(es) recorded" in response.data
    assert b"swell" in response.data


def test_search_history_survives_database_outage(client, monkeypatch):
    monkeypatch.setattr(search_routes, "recent_events", lambda: (None, None))
    response = client.get("/search/history")
    assert response.status_code == 200
    assert b"temporarily unavailable" in response.data


def test_acquire_all_command_saves_every_break(app, db, monkeypatch, fake_panel):
    import services.forecast_service as forecast_service
    monkeypatch.setattr(forecast_service, "build_break_panel", lambda *a, **k: fake_panel())
    result = app.test_cli_runner().invoke(args=["acquire-all"])
    assert result.exit_code == 0, result.output
    assert "Saved 11 new reading(s)" in result.output
    assert db.session.query(Reading).count() > 11
