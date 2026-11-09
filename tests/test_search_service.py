from datetime import datetime

import pytest
from sqlalchemy.exc import OperationalError

from models.reading import Reading
from models.search_event import SearchEvent
from services import search_service
from services.search_service import (
    build_statement,
    log_search,
    normalize_query,
    parse_filters,
    parse_page,
    parse_sort,
    record_selection,
    run_search,
)

NOW = datetime(2026, 11, 9, 12, 0)
BREAKS = [
    {"id": "rincon", "name": "Rincon"},
    {"id": "south-jetty", "name": "South Jetty"},
]
BREAK_IDS = [b["id"] for b in BREAKS]


def add(db, title, description=None, break_id="rincon", source="crowdsurf-user",
        kind="note", retrieved_at=datetime(2026, 11, 1, 12, 0)):
    reading = Reading(title=title, description=description, source=source, kind=kind,
                      external_id=f"{break_id}:{title}:{retrieved_at.isoformat()}",
                      retrieved_at=retrieved_at, break_id=break_id)
    db.session.add(reading)
    db.session.commit()
    return reading


def ids_for(db, q="", sort=None, **filters):
    query = normalize_query(q)
    stmt = build_statement(query, filters, parse_sort(sort, bool(query["tokens"])), BREAKS, NOW)
    return [r.id for r in db.session.execute(stmt).scalars()]


# --- query processing -----------------------------------------------------

def test_normalize_collapses_whitespace_and_case_but_keeps_raw():
    q = normalize_query("  South   JETTY\tswell ")
    assert q["raw"] == "South   JETTY\tswell"
    assert q["normalized"] == "south jetty swell"
    assert q["tokens"] == ["south", "jetty", "swell"]
    assert not q["truncated"]


def test_whitespace_only_query_is_empty():
    assert normalize_query("   \t ")["tokens"] == []
    assert normalize_query(None)["tokens"] == []


def test_long_query_is_truncated():
    q = normalize_query("a" * 150)
    assert q["truncated"]
    assert len(q["normalized"]) == search_service.MAX_QUERY


def test_like_wildcards_match_literally(db):
    percent = add(db, "100% offshore")
    add(db, "1000 waves")
    underscore = add(db, "a_b test")
    add(db, "axb test")
    assert ids_for(db, "100%") == [percent.id]
    assert ids_for(db, "a_b") == [underscore.id]


# --- parsing URL values ------------------------------------------------------

def test_unknown_filter_values_are_ignored_with_notice():
    filters, notices = parse_filters({"source": "evil'; DROP", "kind": "forecast", "break_id": "nowhere"}, BREAK_IDS)
    assert filters == {"kind": "forecast"}
    assert len(notices) == 2


def test_bad_and_reversed_dates_are_ignored():
    filters, notices = parse_filters({"date_from": "11/09/2026"}, BREAK_IDS)
    assert filters == {} and "dates must look like" in notices[0]
    filters, notices = parse_filters({"date_from": "2026-11-09", "date_to": "2026-11-01"}, BREAK_IDS)
    assert filters == {} and "start date is after" in notices[0]


@pytest.mark.parametrize("value", ["abc", "0", "-3", ""])
def test_bad_page_numbers_become_page_one(value):
    page, _ = parse_page(value)
    assert page == 1


def test_sort_is_whitelisted():
    assert parse_sort("DROP TABLE", has_keyword=True) == "relevance"
    assert parse_sort("relevance", has_keyword=False) == "newest"
    assert parse_sort("title", has_keyword=False) == "title"


# --- retrieval, filters, ranking ------------------------------------------

def test_every_token_must_match_some_field(db):
    both = add(db, "Big swell", description="offshore all morning")
    add(db, "Big swell", description="onshore and messy", retrieved_at=datetime(2026, 11, 2))
    assert ids_for(db, "swell offshore") == [both.id]


def test_break_name_matches_through_breaks_json(db):
    note = add(db, "Glassy dawn patrol", break_id="south-jetty")
    add(db, "Glassy dawn patrol", break_id="rincon", retrieved_at=datetime(2026, 11, 2))
    assert ids_for(db, "jetty") == [note.id]


def test_filters_combine_with_keyword(db):
    match = add(db, "Swell check", source="noaa-ndbc-realtime", kind="observation")
    add(db, "Swell check", source="crowdsurf-user", kind="observation", retrieved_at=datetime(2026, 11, 2))
    add(db, "Swell check", source="noaa-ndbc-realtime", kind="forecast", retrieved_at=datetime(2026, 11, 3))
    assert ids_for(db, "swell", source="noaa-ndbc-realtime", kind="observation") == [match.id]


def test_date_range_includes_the_whole_end_day(db):
    inside = add(db, "Late session", retrieved_at=datetime(2026, 11, 5, 23, 30))
    add(db, "Too late", retrieved_at=datetime(2026, 11, 6, 0, 30))
    assert ids_for(db, date_from="2026-11-05", date_to="2026-11-05") == [inside.id]


def test_title_match_outranks_description_match(db):
    in_description = add(db, "Morning report", description="small swell", retrieved_at=datetime(2026, 11, 3))
    in_title = add(db, "Swell building", retrieved_at=datetime(2026, 11, 1))
    assert ids_for(db, "swell") == [in_title.id, in_description.id]


def test_recent_reading_wins_a_tie_and_ties_are_stable(db):
    old = add(db, "Swell", retrieved_at=datetime(2026, 10, 1))
    recent = add(db, "Swell", retrieved_at=datetime(2026, 11, 9, 6, 0))
    assert ids_for(db, "swell") == [recent.id, old.id]
    assert ids_for(db, "swell", sort="oldest") == [old.id, recent.id]


def test_title_sort(db):
    b = add(db, "B swell")
    a = add(db, "A swell", retrieved_at=datetime(2026, 11, 2))
    assert ids_for(db, "swell", sort="title") == [a.id, b.id]


# --- run_search: states and pagination ---------------------------------------

def test_before_state_does_not_touch_the_database(db, monkeypatch):
    monkeypatch.setattr(search_service.db, "paginate", lambda *a, **k: pytest.fail("queried"))
    assert run_search({"q": "   "}, BREAKS)["state"] == "before"


def test_filters_without_keyword_are_a_filtered_browse(db):
    add(db, "Anything", kind="forecast")
    result = run_search({"kind": "forecast"}, BREAKS)
    assert result["state"] == "results"
    assert result["sort"] == "newest"


def test_page_past_the_end_shows_last_page(db):
    for day in range(1, 13):
        add(db, f"Swell {day}", retrieved_at=datetime(2026, 11, day))
    result = run_search({"q": "swell", "page": "99999"}, BREAKS, per_page=10)
    assert result["pagination"].page == 2
    assert len(result["pagination"].items) == 2
    assert any("only 2 page" in n for n in result["notices"])


def test_no_results_state(db):
    add(db, "Swell")
    assert run_search({"q": "tsunami"}, BREAKS)["state"] == "empty"


def test_database_failure_gives_error_state(db, monkeypatch):
    def boom(*args, **kwargs):
        raise OperationalError("SELECT", {}, Exception("connection refused"))
    monkeypatch.setattr(search_service.db, "paginate", boom)
    assert run_search({"q": "swell"}, BREAKS)["state"] == "error"


# --- telemetry ---------------------------------------------------------------

def test_log_search_records_event(db):
    result = run_search({"q": " Rincon  SWELL ", "kind": "note"}, BREAKS)
    event = db.session.get(SearchEvent, log_search(result, "sid-1"))
    assert event.query_raw == "Rincon  SWELL"
    assert event.query_normalized == "rincon swell"
    assert event.filters_json == {"kind": "note"}
    assert event.no_result and event.result_count == 0


def test_telemetry_failure_does_not_raise(db, monkeypatch):
    result = run_search({"q": "swell"}, BREAKS)

    def boom():
        raise OperationalError("INSERT", {}, Exception("down"))
    monkeypatch.setattr(search_service.db.session, "commit", boom)
    assert log_search(result, "sid-1") is None


def test_selection_only_updates_own_session(db):
    reading = add(db, "Swell")
    event_id = log_search(run_search({"q": "swell"}, BREAKS), "sid-1")
    record_selection(event_id, 1, reading.id, "someone-else")
    assert db.session.get(SearchEvent, event_id).selected_reading_id is None
    record_selection(event_id, 1, reading.id, "sid-1")
    event = db.session.get(SearchEvent, event_id)
    assert (event.selected_reading_id, event.selected_rank) == (reading.id, 1)
