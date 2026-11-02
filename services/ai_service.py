"""Grounded AI summary of a break's *saved* readings, using the Claude API.

Flow: stored readings -> bounded context -> Claude -> grounding check ->
saved as a Reading (kind="summary") with model/prompt metadata.

Design rules (from the P2 proposal and the course's A5 notes):
- Grounded: Claude only sees readings already stored in the database,
  never the open web, and is told to use nothing else.
- No data, no summary: with zero stored readings it doesn't call the API.
- Bounded context: only the newest reading per source plus a few user
  notes, as short text lines (not the full raw JSON).
- Validated: every number in the answer is checked against the numbers in
  the context. Unsupported numbers are recorded and shown as a warning.
- Metadata recorded: model, prompt version, input reading ids, token
  usage and time are stored with the summary.
- Graceful failure: a missing key or API error returns a friendly message;
  the page keeps working.
"""

import logging
import re
from datetime import datetime, timezone

import anthropic
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models.reading import KIND_NOTE, KIND_SUMMARY, Reading
from services.reading_service import SaveResult, commit_or_rollback, latest_readings_for_break
from services.source_registry import AI_SOURCE, SOURCE_LABELS

log = logging.getLogger(__name__)

PROMPT_VERSION = "break-summary-v1"
MAX_NOTES = 5
MAX_OUTPUT_TOKENS = 2000  # the summary is deliberately short
DOCS_URL = "https://platform.claude.com/docs/en/api/messages"

SYSTEM_PROMPT = """You write short surf-condition summaries for Crowdsurf, a surf \
forecast app for Ventura and Santa Barbara county breaks.

You will get a list of saved readings for one surf break. Each reading has a \
source (a forecast model, a buoy, a tide station, or a surfer's note) and the \
time it was retrieved. Write a summary for a surfer deciding whether to go.

Rules:
- Use only the facts in the readings. Do not add outside knowledge about the \
break, typical conditions, or anything not listed.
- When you state a number, copy it exactly as it appears in the readings, with \
its unit.
- If forecast and observed (buoy) numbers disagree, say so plainly.
- If readings are old (more than a few hours) or a key source is missing, say \
what is missing instead of guessing.
- Name the source for each key claim in parentheses, e.g. (NDBC buoy).
- 80 to 140 words, plain text, no headings or bullet points. Do not tell the \
surfer what to decide; describe the conditions."""

NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def build_context(readings):
    """Turn readings into the bounded text block Claude will see.

    Keeps the newest reading per source (readings arrive newest-first) plus
    up to MAX_NOTES user notes. Returns (context_text, used_readings).
    """
    used = []
    seen_sources = set()
    notes = 0
    for r in readings:
        if r.kind == KIND_SUMMARY:
            continue
        if r.kind == KIND_NOTE:
            if notes >= MAX_NOTES:
                continue
            notes += 1
        elif r.source in seen_sources:
            continue
        seen_sources.add(r.source)
        used.append(r)

    lines = []
    for r in used:
        label = SOURCE_LABELS.get(r.source, r.source)
        line = f"- [{label}] retrieved {r.retrieved_at.strftime('%Y-%m-%d %H:%M')} UTC: {r.description or r.title}"
        if r.kind == KIND_NOTE and r.data_json:
            values = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in r.data_json.items())
            line += f" ({values})"
        lines.append(line)
    return "\n".join(lines), used


def _numbers(text):
    return [float(n) for n in NUMBER_RE.findall(text)]


def find_unsupported_numbers(summary, context):
    """Return numbers in the summary that don't appear in the context.

    A number counts as supported if some context number is within 0.05 of
    it, so "5.9" matches "5.9" but "8" doesn't match "5.9". Small whole
    numbers (0-3) are ignored because they are usually words like "one"
    or "two sources" written as digits.
    """
    available = _numbers(context)
    unsupported = []
    for n in _numbers(summary):
        if n.is_integer() and 0 <= n <= 3:
            continue
        if not any(abs(n - a) <= 0.05 for a in available):
            unsupported.append(n)
    return unsupported


def _call_claude(api_key, model, context, break_name):
    """Send one request to the Claude Messages API and return the response."""
    client = anthropic.Anthropic(api_key=api_key, timeout=60.0, max_retries=2)
    user_message = (
        f"Break: {break_name}\n"
        f"Current time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC\n\n"
        f"Saved readings:\n{context}"
    )
    # fallbacks="default": if a safety classifier declines this request,
    # the API re-runs it on a suitable fallback model inside the same call.
    return client.beta.messages.create(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )


def generate_break_summary(break_record, api_key, model):
    """Create and store a grounded summary for one break. Returns a SaveResult."""
    if not api_key:
        return SaveResult(False, "AI summaries are off: ANTHROPIC_API_KEY is not set in .env.", status=503)

    readings = latest_readings_for_break(break_record["id"], limit=60)
    context, used = build_context(readings)
    if not used:
        return SaveResult(
            False,
            "No saved readings for this break yet. Click \"Save this snapshot\" first, then summarize.",
            status=400,
        )

    try:
        response = _call_claude(api_key, model, context, break_record["name"])
    except anthropic.AuthenticationError:
        return SaveResult(False, "The Claude API key was rejected. Check ANTHROPIC_API_KEY.", status=502)
    except anthropic.RateLimitError:
        return SaveResult(False, "Claude API rate limit reached. Try again in a minute.", status=503)
    except anthropic.APIStatusError as exc:
        log.warning("Claude API error %s", exc.status_code)
        return SaveResult(False, f"The Claude API returned an error ({exc.status_code}). Try again later.", status=502)
    except anthropic.APIConnectionError:
        return SaveResult(False, "Couldn't reach the Claude API. Check the internet connection.", status=503)

    if response.stop_reason == "refusal":
        return SaveResult(False, "Claude declined to summarize these readings.", status=502)

    summary = "".join(block.text for block in response.content if block.type == "text").strip()
    if not summary:
        return SaveResult(False, "Claude returned an empty summary. Nothing was saved.", status=502)

    unsupported = find_unsupported_numbers(summary, context)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    reading = Reading(
        title=f"{break_record['name']}: AI summary, {now.strftime('%Y-%m-%d %H:%M')} UTC",
        description=summary,
        source=AI_SOURCE["slug"],
        source_url=DOCS_URL,
        external_id=f"{break_record['id']}:summary:{now.strftime('%Y%m%dT%H%M%S')}",
        retrieved_at=now,
        break_id=break_record["id"],
        kind=KIND_SUMMARY,
        data_json={
            "model_requested": model,
            "model_served": response.model,
            "prompt_version": PROMPT_VERSION,
            "input_reading_ids": [r.id for r in used],
            "unsupported_numbers": unsupported,
            "grounded": not unsupported,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "request_id": getattr(response, "_request_id", None),
        },
    )
    db.session.add(reading)
    message = "AI summary saved."
    if unsupported:
        message += " Warning: some numbers in it weren't found in the saved readings."
    return commit_or_rollback(message, reading)


def latest_summary(break_id):
    """Newest stored AI summary for a break, or None (also None if the DB is down)."""
    try:
        return db.session.execute(
            select(Reading)
            .filter_by(break_id=break_id, kind=KIND_SUMMARY)
            .order_by(Reading.retrieved_at.desc())
            .limit(1)
        ).scalar_one_or_none()
    except SQLAlchemyError:
        db.session.rollback()
        log.exception("Could not load the latest AI summary")
        return None
