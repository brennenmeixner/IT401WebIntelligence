from datetime import datetime

from sqlalchemy.exc import OperationalError

from models.reading import Reading
from services import reading_service
from services.external_common import failed_result
from services.reading_service import (
    create_manual_reading,
    delete_reading,
    describe_panel_result,
    list_readings,
    save_panel_snapshot,
    stored_fallbacks,
    update_reading,
    validate_reading_form,
)

BREAK_IDS = {"south-jetty", "rincon"}
FIXED_NOW = datetime(2026, 11, 1, 18, 25)


def valid_form(**overrides):
    form = {
        "break_id": "rincon",
        "title": "  Head high and clean  ",
        "description": "Light offshore.",
        "kind": "observation",
        "wave_height_ft": "5",
        "retrieved_at": "2026-11-01T07:30",
    }
    form.update(overrides)
    return form


# --- validation -------------------------------------------------------------

def test_valid_form_is_cleaned():
    cleaned, errors = validate_reading_form(valid_form(), BREAK_IDS)
    assert errors == []
    assert cleaned["title"] == "Head high and clean"  # whitespace trimmed
    assert cleaned["measurements"] == {"wave_height_ft": 5.0}
    # The form is Pacific time. DST ended at 2am on Nov 1 2026, so 07:30 PST = 15:30 UTC.
    assert cleaned["retrieved_at"] == datetime(2026, 11, 1, 15, 30)


def test_missing_title_and_bad_break_are_rejected():
    _, errors = validate_reading_form(valid_form(title="  ", break_id="not-a-break"), BREAK_IDS)
    assert "Title is required." in errors
    assert "Pick a break from the list." in errors


def test_out_of_range_and_non_numeric_values_are_rejected():
    _, errors = validate_reading_form(valid_form(wave_height_ft="300", period_s="abc"), BREAK_IDS)
    assert any("between 0 and 60" in e for e in errors)
    assert any("must be a number" in e for e in errors)


def test_bad_url_kind_and_date_are_rejected():
    _, errors = validate_reading_form(
        valid_form(source_url="javascript:alert(1)", kind="summary", retrieved_at="yesterday"),
        BREAK_IDS,
    )
    assert any("Source URL" in e for e in errors)
    assert any("Kind must be" in e for e in errors)
    assert any("not a valid date" in e for e in errors)


def test_missing_optional_values_are_fine():
    cleaned, errors = validate_reading_form({"break_id": "rincon", "title": "Flat"}, BREAK_IDS)
    assert errors == []
    assert cleaned["description"] is None
    assert cleaned["measurements"] == {}
    assert cleaned["kind"] == "note"


# --- CRUD ---------------------------------------------------------------------

def test_create_then_duplicate_is_rejected(db):
    cleaned, _ = validate_reading_form(valid_form(), BREAK_IDS)
    first = create_manual_reading(cleaned)
    assert first.ok
    second = create_manual_reading(cleaned)
    assert not second.ok
    assert second.status == 409
    assert db.session.query(Reading).count() == 1


def test_update_manual_reading_changes_values(db):
    cleaned, _ = validate_reading_form(valid_form(), BREAK_IDS)
    reading = create_manual_reading(cleaned).reading
    new_values, _ = validate_reading_form(valid_form(title="Bigger", wave_height_ft="7"), BREAK_IDS, editing=True)
    result = update_reading(reading, new_values)
    assert result.ok
    assert reading.title == "Bigger"
    assert reading.data_json == {"wave_height_ft": 7.0}
    assert reading.updated_at is not None


def test_update_api_reading_keeps_provenance(db, south_jetty, fake_panel):
    save_panel_snapshot(south_jetty, fake_panel(), now=FIXED_NOW)
    reading = db.session.query(Reading).filter_by(source="open-meteo-marine").one()
    original_data = reading.data_json
    original_url = reading.source_url
    edits, _ = validate_reading_form(
        {"title": "Renamed", "kind": "forecast", "source_url": "https://evil.example", "wave_height_ft": "9"},
        BREAK_IDS,
        editing=True,
    )
    update_reading(reading, edits)
    assert reading.title == "Renamed"
    assert reading.source_url == original_url
    assert reading.data_json == original_data


def test_delete_reading(db):
    cleaned, _ = validate_reading_form(valid_form(), BREAK_IDS)
    reading = create_manual_reading(cleaned).reading
    assert delete_reading(reading).ok
    assert db.session.query(Reading).count() == 0


def test_database_error_rolls_back_with_friendly_message(db, monkeypatch):
    def broken_commit():
        raise OperationalError("INSERT", {}, Exception("MySQL server has gone away"))

    monkeypatch.setattr(db.session, "commit", broken_commit)
    cleaned, _ = validate_reading_form(valid_form(), BREAK_IDS)
    result = create_manual_reading(cleaned)
    assert not result.ok
    assert result.status == 500
    assert "Nothing was saved" in result.message


def test_list_readings_filters_by_source(db, south_jetty, fake_panel):
    save_panel_snapshot(south_jetty, fake_panel(), now=FIXED_NOW)
    page = list_readings(source="noaa-ndbc-realtime")
    assert page.total == 1
    assert list_readings(break_id="rincon").total == 0
    # an unknown source is ignored instead of erroring
    assert list_readings(source="not-a-source").total == 11


# --- persisting API results ----------------------------------------------------

def test_snapshot_saves_live_sources_and_skips_failed_ones(db, south_jetty, fake_panel):
    outcome = save_panel_snapshot(south_jetty, fake_panel(), now=FIXED_NOW)
    assert outcome["ok"]
    # 13 persistable sources, 2 are down in the fake panel (water temp, RapidAPI)
    assert outcome["created"] == 11
    assert "WeatherAPI.com Marine (RapidAPI)" in outcome["skipped"]

    reading = db.session.query(Reading).filter_by(source="noaa-ndbc-scrape").one()
    assert reading.external_id == "south-jetty:noaa-ndbc-scrape:20261101T18"
    assert reading.source_url == "https://www.ndbc.noaa.gov/station_page.php?station=46053"
    assert reading.kind == "observation"
    assert reading.data_json["wave_height_ft"] == 5.9


def test_second_snapshot_in_same_hour_updates_instead_of_duplicating(db, south_jetty, fake_panel):
    save_panel_snapshot(south_jetty, fake_panel(), now=FIXED_NOW)
    outcome = save_panel_snapshot(south_jetty, fake_panel(), now=FIXED_NOW.replace(minute=50))
    assert outcome["created"] == 0
    assert outcome["updated"] == 11
    assert db.session.query(Reading).count() == 11


def test_describe_marine_result():
    text = describe_panel_result("marine", {"hourly": {"wave_height": [1.0], "swell_wave_height": [None], "swell_wave_period": [13]}})
    assert text == "Next hour: wave 3.3 ft, 13 s period"


def test_describe_handles_unexpected_shapes():
    assert describe_panel_result("marine", {"unexpected": True}) is None
    assert describe_panel_result("nws_forecast", None) is None


# --- reusing stored data when a source is down ---------------------------------

def test_failed_source_falls_back_to_stored_copy(db, south_jetty, fake_panel):
    save_panel_snapshot(south_jetty, fake_panel(), now=FIXED_NOW)
    panel = fake_panel(marine=failed_result("Open-Meteo Marine Weather API", "timeout"))

    panel = stored_fallbacks("south-jetty", panel)

    assert panel["marine"]["live"] is True
    assert panel["marine"]["stored"] is True
    assert panel["marine"]["data"]["hourly"]["wave_height"] == [1.0]


def test_failed_source_without_stored_copy_stays_failed(db, fake_panel):
    panel = stored_fallbacks("south-jetty", fake_panel())
    assert panel["rapid_marine"]["live"] is False


def test_fallback_survives_a_database_outage(db, fake_panel, monkeypatch):
    def broken_execute(*args, **kwargs):
        raise OperationalError("SELECT", {}, Exception("connection refused"))

    monkeypatch.setattr(reading_service.db.session, "execute", broken_execute)
    panel = stored_fallbacks("south-jetty", fake_panel())
    assert panel["rapid_marine"]["live"] is False


def test_tide_curve_description_has_low_and_high():
    from services.reading_service import describe_panel_result
    curve = [
        {"time": "2026-11-01 20:00", "height_ft": 0.5},
        {"time": "2026-11-01 22:00", "height_ft": -0.1},
        {"time": "2026-11-02 04:00", "height_ft": 3.9},
    ]
    text = describe_panel_result("tide_curve", curve)
    assert "lowest -0.1 ft at 2026-11-01 22:00" in text
    assert "highest 3.9 ft" in text
    assert "local time" in text


def test_missing_buoy_period_is_shown_as_na_not_none():
    from services.reading_service import describe_panel_result
    data = {"latest": {"wave_height_ft": 6.2, "dominant_period_s": None, "time_utc": "2026-11-02T04:40Z"}, "rows": [1]}
    text = describe_panel_result("buoy_history", data)
    assert "6.2 ft @ n/a" in text
    assert "None" not in text
