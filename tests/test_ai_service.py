from datetime import datetime
from types import SimpleNamespace

import anthropic
import httpx2

from models.reading import Reading
from services import ai_service
from services.ai_service import build_context, find_unsupported_numbers, generate_break_summary
from services.reading_service import save_panel_snapshot


def fake_response(text, stop_reason="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        model="claude-opus-5-5",
        usage=SimpleNamespace(input_tokens=120, output_tokens=40),
        _request_id="req_test",
    )


def test_context_keeps_newest_reading_per_source(db):
    older = Reading(title="old", description="wave 2 ft", source="noaa-ndbc-scrape", external_id="a",
                    retrieved_at=datetime(2026, 1, 1, 0), break_id="south-jetty", kind="observation")
    newer = Reading(title="new", description="wave 5.9 ft", source="noaa-ndbc-scrape", external_id="b",
                    retrieved_at=datetime(2026, 1, 1, 6), break_id="south-jetty", kind="observation")
    summary = Reading(title="s", description="old summary", source="anthropic-claude", external_id="c",
                      retrieved_at=datetime(2026, 1, 1, 7), break_id="south-jetty", kind="summary")
    context, used = build_context([summary, newer, older])
    assert used == [newer]
    assert "wave 5.9 ft" in context
    assert "old summary" not in context


def test_unsupported_numbers_are_flagged():
    context = "- [NDBC] wave 5.9 ft @ 7.0 s"
    assert find_unsupported_numbers("Waves 5.9 ft at 7 s.", context) == []
    assert find_unsupported_numbers("Waves 8.5 ft at 7 s.", context) == [8.5]


def test_no_api_key_means_no_call(db, south_jetty):
    result = generate_break_summary(south_jetty, api_key=None, model="claude-opus-5-5")
    assert not result.ok
    assert "ANTHROPIC_API_KEY" in result.message


def test_no_saved_readings_means_no_summary(db, south_jetty, monkeypatch):
    called = []
    monkeypatch.setattr(ai_service, "_call_claude", lambda *a: called.append(1))
    result = generate_break_summary(south_jetty, api_key="sk-test", model="claude-opus-5-5")
    assert not result.ok
    assert "No saved readings" in result.message
    assert called == []


def test_summary_is_saved_with_metadata(db, south_jetty, fake_panel, monkeypatch):
    save_panel_snapshot(south_jetty, fake_panel())
    monkeypatch.setattr(
        ai_service, "_call_claude",
        lambda *a: fake_response("The NDBC buoy shows 5.9 ft at 7 s (NDBC buoy)."),
    )

    result = generate_break_summary(south_jetty, api_key="sk-test", model="claude-opus-5-5")

    assert result.ok
    saved = result.reading
    assert saved.kind == "summary"
    assert saved.source == "anthropic-claude"
    assert saved.data_json["prompt_version"] == ai_service.PROMPT_VERSION
    assert saved.data_json["model_served"] == "claude-opus-5-5"
    assert saved.data_json["grounded"] is True
    assert len(saved.data_json["input_reading_ids"]) == 11


def test_summary_with_made_up_number_is_flagged(db, south_jetty, fake_panel, monkeypatch):
    save_panel_snapshot(south_jetty, fake_panel())
    monkeypatch.setattr(ai_service, "_call_claude", lambda *a: fake_response("Expect 14.2 ft sets."))
    result = generate_break_summary(south_jetty, api_key="sk-test", model="claude-opus-5-5")
    assert result.ok
    assert result.reading.data_json["unsupported_numbers"] == [14.2]
    assert "Warning" in result.message


def test_api_error_returns_friendly_message(db, south_jetty, fake_panel, monkeypatch):
    save_panel_snapshot(south_jetty, fake_panel())

    def raise_connection_error(*args):
        raise anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com"))

    monkeypatch.setattr(ai_service, "_call_claude", raise_connection_error)
    result = generate_break_summary(south_jetty, api_key="sk-test", model="claude-opus-5-5")
    assert not result.ok
    assert "Couldn't reach the Claude API" in result.message
    assert db.session.query(Reading).filter_by(kind="summary").count() == 0


def test_refusal_is_not_saved(db, south_jetty, fake_panel, monkeypatch):
    save_panel_snapshot(south_jetty, fake_panel())
    monkeypatch.setattr(ai_service, "_call_claude", lambda *a: fake_response("", stop_reason="refusal"))
    result = generate_break_summary(south_jetty, api_key="sk-test", model="claude-opus-5-5")
    assert not result.ok
    assert db.session.query(Reading).filter_by(kind="summary").count() == 0
