"""Persistence + validation for Reading records (A3).

Everything that touches the database for readings lives here, so routes
stay thin and this logic can be tested without a browser:

- validate_reading_form(): checks user input before it reaches the DB
- create_manual_reading() / update_reading() / delete_reading(): CRUD
- save_panel_snapshot(): turns live API/scrape results into readings
- latest_readings_for_break() / stored_fallbacks(): read stored data back

Every write uses the same transaction pattern from the course slides:
try -> commit; IntegrityError -> rollback ("already exists");
any other error -> rollback + log + friendly message. Nothing is ever
committed half-way.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from extensions import db
from models.reading import KIND_FORECAST, KIND_NOTE, KIND_OBSERVATION, KINDS, Reading
from services.source_registry import (
    ALLOWED_SOURCES,
    MANUAL_SOURCE,
    PANEL_KEY_BY_SLUG,
    PANEL_SOURCES,
)

log = logging.getLogger(__name__)

TITLE_MAX = 200
DESCRIPTION_MAX = 5000
URL_MAX = 500

# Kinds a person may pick in the web form ("summary" is AI-only).
FORM_KINDS = (KIND_FORECAST, KIND_OBSERVATION, KIND_NOTE)

# Optional numeric measurements on a manual reading: field -> (label, min, max).
# Ranges are generous but rule out typos like 300 ft waves.
MEASUREMENTS = {
    "wave_height_ft": ("Wave height (ft)", 0, 60),
    "period_s": ("Swell period (s)", 0, 30),
    "wind_speed_kt": ("Wind speed (kt)", 0, 100),
    "water_temp_f": ("Water temp (°F)", 32, 95),
}

DATETIME_FORMATS = ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M")

# The form asks for local (Pacific) time; the database stores UTC.
LOCAL_TZ = ZoneInfo("America/Los_Angeles")


class SaveResult:
    """Outcome of a write: ok flag, a message for the user, and the record."""

    def __init__(self, ok, message, reading=None, status=200):
        self.ok = ok
        self.message = message
        self.reading = reading
        self.status = status


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _clean(value):
    """Trim whitespace; treat None as an empty string."""
    return (value or "").strip()


def _parse_datetime(text):
    """Parse a local (Pacific) form date/time and return it as naive UTC."""
    for fmt in DATETIME_FORMATS:
        try:
            local = datetime.strptime(text, fmt).replace(tzinfo=LOCAL_TZ)
        except ValueError:
            continue
        return local.astimezone(timezone.utc).replace(tzinfo=None)
    return None


def utc_to_local_input(value):
    """Format a stored naive-UTC datetime for an <input type="datetime-local">."""
    if value is None:
        return ""
    return value.replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ).strftime("%Y-%m-%dT%H:%M")


def validate_reading_form(form, valid_break_ids, editing=False, allowed_kinds=FORM_KINDS):
    """Check and normalize submitted form fields.

    Returns (cleaned, errors). `cleaned` is only safe to save when `errors`
    is empty. When editing, provenance fields (source, break) are not
    accepted from the form: they describe where the data came from and
    shouldn't be rewritten after the fact.
    """
    errors = []
    cleaned = {}

    title = _clean(form.get("title"))
    if not title:
        errors.append("Title is required.")
    elif len(title) > TITLE_MAX:
        errors.append(f"Title must be {TITLE_MAX} characters or fewer.")
    cleaned["title"] = title

    description = _clean(form.get("description"))
    if len(description) > DESCRIPTION_MAX:
        errors.append(f"Description must be {DESCRIPTION_MAX} characters or fewer.")
    cleaned["description"] = description or None

    kind = _clean(form.get("kind")) or KIND_NOTE
    if kind not in allowed_kinds:
        errors.append("Kind must be one of: " + ", ".join(allowed_kinds) + ".")
    cleaned["kind"] = kind

    source_url = _clean(form.get("source_url"))
    if source_url:
        if not re.match(r"^https?://[^\s]+$", source_url):
            errors.append("Source URL must start with http:// or https://.")
        elif len(source_url) > URL_MAX:
            errors.append(f"Source URL must be {URL_MAX} characters or fewer.")
    cleaned["source_url"] = source_url or None

    retrieved_text = _clean(form.get("retrieved_at"))
    if retrieved_text:
        retrieved_at = _parse_datetime(retrieved_text)
        if retrieved_at is None:
            errors.append("Observed date/time is not a valid date.")
        elif retrieved_at > utc_now() + timedelta(days=1):
            errors.append("Observed date/time can't be in the future.")
        cleaned["retrieved_at"] = retrieved_at
    else:
        cleaned["retrieved_at"] = utc_now()

    measurements = {}
    for field, (label, low, high) in MEASUREMENTS.items():
        raw = _clean(form.get(field))
        if not raw:
            continue  # optional: a missing value is simply left out
        try:
            number = float(raw)
        except ValueError:
            errors.append(f"{label} must be a number.")
            continue
        if not low <= number <= high:
            errors.append(f"{label} must be between {low} and {high}.")
            continue
        measurements[field] = number
    cleaned["measurements"] = measurements

    if not editing:
        break_id = _clean(form.get("break_id"))
        if break_id not in valid_break_ids:
            errors.append("Pick a break from the list.")
        cleaned["break_id"] = break_id

    return cleaned, errors


def _slug(text, max_len=40):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:max_len]


def manual_external_id(break_id, title, retrieved_at):
    """Duplicate rule for manual entries: same break + same title + same minute."""
    return f"{break_id}:{retrieved_at.strftime('%Y%m%dT%H%M')}:{_slug(title)}"[:120]


# ---------------------------------------------------------------------------
# Transaction helper
# ---------------------------------------------------------------------------

def commit_or_rollback(success_message, reading=None, duplicate_message="This reading already exists."):
    try:
        db.session.commit()
        return SaveResult(True, success_message, reading)
    except IntegrityError:
        db.session.rollback()
        return SaveResult(False, duplicate_message, None, status=409)
    except SQLAlchemyError:
        db.session.rollback()
        log.exception("Database error while saving a reading")
        return SaveResult(False, "The database is unavailable right now. Nothing was saved.", None, status=500)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_manual_reading(cleaned):
    """Insert a user-entered reading. `cleaned` comes from validate_reading_form."""
    external_id = manual_external_id(cleaned["break_id"], cleaned["title"], cleaned["retrieved_at"])

    existing = db.session.execute(
        select(Reading).filter_by(source=MANUAL_SOURCE["slug"], external_id=external_id)
    ).scalar_one_or_none()
    if existing is not None:
        return SaveResult(False, "An identical reading (same break, title and time) already exists.", existing, status=409)

    reading = Reading(
        title=cleaned["title"],
        description=cleaned["description"],
        source=MANUAL_SOURCE["slug"],
        source_url=cleaned["source_url"],
        external_id=external_id,
        retrieved_at=cleaned["retrieved_at"],
        break_id=cleaned["break_id"],
        kind=cleaned["kind"],
        data_json=cleaned["measurements"] or None,
    )
    db.session.add(reading)
    return commit_or_rollback("Reading saved.", reading)


def update_reading(reading, cleaned):
    """Change the editable fields of an existing reading."""
    reading.title = cleaned["title"]
    reading.description = cleaned["description"]
    reading.kind = cleaned["kind"]
    if reading.source == MANUAL_SOURCE["slug"]:
        # Only hand-entered readings may change their URL/time/values;
        # API readings keep the provenance and raw data they were fetched with.
        reading.source_url = cleaned["source_url"]
        reading.retrieved_at = cleaned["retrieved_at"]
        reading.data_json = cleaned["measurements"] or None
    return commit_or_rollback("Reading updated.", reading)


def delete_reading(reading):
    db.session.delete(reading)
    return commit_or_rollback("Reading deleted.")


def get_reading(reading_id):
    return db.session.get(Reading, reading_id)


def list_readings(page=1, per_page=20, break_id=None, source=None, kind=None):
    """Newest-first, optionally filtered, paginated list of readings."""
    query = select(Reading)
    if break_id:
        query = query.filter_by(break_id=break_id)
    if source and source in ALLOWED_SOURCES:
        query = query.filter_by(source=source)
    if kind and kind in KINDS:
        query = query.filter_by(kind=kind)
    query = query.order_by(Reading.retrieved_at.desc(), Reading.id.desc())
    return db.paginate(query, page=page, per_page=per_page, error_out=False)


def count_readings():
    return db.session.query(Reading).count()


# ---------------------------------------------------------------------------
# Persisting live API / scrape results
# ---------------------------------------------------------------------------

def _first(values):
    return values[0] if isinstance(values, list) and values else None


def _or_na(value, unit=""):
    """Format a possibly-missing number: 5.9 -> '5.9 ft', None -> 'n/a'."""
    return "n/a" if value is None else f"{value}{unit}"


def describe_panel_result(key, data):
    """One readable sentence summarizing what a source returned.

    This becomes the reading's description. Missing values are skipped
    rather than shown as "None".
    """
    try:
        if key == "marine":
            h = data["hourly"]
            wave = _first(h.get("wave_height"))
            swell = _first(h.get("swell_wave_height"))
            period = _first(h.get("swell_wave_period"))
            parts = []
            if wave is not None:
                parts.append(f"wave {wave * 3.28084:.1f} ft")
            if swell is not None:
                parts.append(f"swell {swell * 3.28084:.1f} ft")
            if period is not None:
                parts.append(f"{period:.0f} s period")
            return "Next hour: " + ", ".join(parts) if parts else None
        if key == "weather":
            h = data["hourly"]
            wind = _first(h.get("wind_speed_10m"))
            temp = _first(h.get("temperature_2m"))
            parts = []
            if wind is not None:
                parts.append(f"wind {wind * 0.539957:.0f} kt")
            if temp is not None:
                parts.append(f"air {temp:.0f}°C")
            return "Next hour: " + ", ".join(parts) if parts else None
        if key == "nws_forecast":
            first = _first(data.get("periods"))
            return f"{first['name']}: {first['short_forecast']}" if first else None
        if key == "nws_alerts":
            return f"{len(data)} active alert(s)" if data else "No active alerts"
        if key == "tide_predictions":
            text = "; ".join(
                f"{'High' if p['type'] == 'H' else 'Low'} {p['height_ft']} ft at {p['time']}" for p in data
            )
            # CO-OPS is asked for local station time (lst_ldt); say so, or a
            # reader comparing against UTC timestamps gets the day wrong.
            return f"{text} (local time)" if text else None
        if key == "tide_curve":
            points = [p for p in data if p.get("height_ft") is not None]
            if not points:
                return None
            low = min(points, key=lambda p: p["height_ft"])
            high = max(points, key=lambda p: p["height_ft"])
            return (
                f"Tide curve {points[0]['time']} to {points[-1]['time']} (local time): "
                f"lowest {low['height_ft']} ft at {low['time']}, highest {high['height_ft']} ft at {high['time']}"
            )
        if key == "water_temp":
            return f"Water {data.get('value_f')}°F at {data.get('time')}"
        if key == "spc_outlook":
            return f"Thunderstorm risk: {data.get('label')}" if data.get("active") else "No elevated thunderstorm risk"
        if key == "buoy_reading":
            labels = {
                "wave_height_ft": "waves {} ft", "dominant_period_s": "{} s period",
                "wind_speed_kt": "wind {} kt", "wind_direction": "from {}",
                "water_temp_f": "water {}°F", "pressure_in": "pressure {} in",
            }
            parts = [labels[k].format(v) for k, v in data.items() if k in labels]
            return "Observed: " + ", ".join(parts) if parts else None
        if key == "buoy_history":
            latest = data.get("latest")
            if latest:
                return (
                    f"Latest observed: {_or_na(latest['wave_height_ft'], ' ft')} @ {_or_na(latest['dominant_period_s'], ' s')} "
                    f"({latest['time_utc']}), {len(data.get('rows', []))} rows"
                )
            return "Station reported no wave rows"
        if key == "rapid_marine":
            first = _first(data.get("hours"))
            if first and data.get("mode") == "weather":
                return (
                    f"Second opinion (weather only): wind {first['wind_kph']} kph {first['wind_direction']}, "
                    f"gusts {first.get('gust_kph')} kph, {first.get('condition')}"
                )
            if first:
                return (
                    f"Second opinion: swell {_or_na(first['swell_height_ft'], ' ft')} @ {_or_na(first['swell_period_s'], ' s')} "
                    f"from {first['swell_direction']}"
                )
            return None
        if key == "sun_moon":
            return (
                f"First light {data.get('first_light')}, sunset {data.get('sunset')}, "
                f"moon {data.get('moon_phase')}"
            )
        if key == "beach_quality":
            n = len(data.get("advisories", []))
            return f"{n} recent advisory record(s) within {data.get('radius_km')} km"
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    return None


def snapshot_external_id(break_id, slug, when):
    """Duplicate rule for API snapshots: one reading per break + source + hour.

    Saving twice in the same hour updates that hour's reading instead of
    adding a near-identical copy.
    """
    return f"{break_id}:{slug}:{when.strftime('%Y%m%dT%H')}"


def save_panel_snapshot(break_record, panel, now=None):
    """Persist every live source in a break panel as a Reading.

    Returns a dict: {"created": n, "updated": n, "skipped": [labels],
    "ok": bool, "message": str}. Sources that were down are skipped (there
    is nothing to save). Everything is committed in one transaction.
    """
    now = now or utc_now()
    created, updated, skipped = 0, 0, []

    for key, meta in PANEL_SOURCES.items():
        result = panel.get(key)
        if not result or not result.get("live") or result.get("stored"):
            skipped.append(meta["label"])
            continue

        external_id = snapshot_external_id(break_record["id"], meta["slug"], now)
        retrieved_at = _parse_iso(result.get("fetched_at")) or now
        title = f"{break_record['name']}: {meta['label']}, {now.strftime('%Y-%m-%d %H:00')} UTC"
        description = describe_panel_result(key, result.get("data")) or f"Snapshot of {meta['label']}"

        existing = db.session.execute(
            select(Reading).filter_by(source=meta["slug"], external_id=external_id)
        ).scalar_one_or_none()

        if existing is None:
            db.session.add(
                Reading(
                    title=title[:TITLE_MAX],
                    description=description,
                    source=meta["slug"],
                    source_url=meta["url"](break_record),
                    external_id=external_id,
                    retrieved_at=retrieved_at,
                    break_id=break_record["id"],
                    kind=meta["kind"],
                    data_json=result.get("data"),
                )
            )
            created += 1
        else:
            existing.description = description
            existing.retrieved_at = retrieved_at
            existing.data_json = result.get("data")
            updated += 1

    outcome = commit_or_rollback("saved", duplicate_message="Another save for this hour happened at the same time. Try again.")
    if not outcome.ok:
        return {"ok": False, "message": outcome.message, "created": 0, "updated": 0, "skipped": skipped}

    message = f"Saved {created} new reading(s)"
    if updated:
        message += f", refreshed {updated} already saved this hour"
    if skipped:
        message += f". Skipped (unavailable): {', '.join(skipped)}"
    return {"ok": True, "message": message + ".", "created": created, "updated": updated, "skipped": skipped}


def _parse_iso(text):
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


# ---------------------------------------------------------------------------
# Reading stored data back
# ---------------------------------------------------------------------------

def latest_readings_for_break(break_id, limit=40, exclude_kinds=()):
    """Most recent readings for one break, newest first."""
    query = select(Reading).filter_by(break_id=break_id)
    if exclude_kinds:
        query = query.filter(Reading.kind.not_in(exclude_kinds))
    query = query.order_by(Reading.retrieved_at.desc(), Reading.id.desc()).limit(limit)
    return list(db.session.execute(query).scalars())


def stored_fallbacks(break_id, panel):
    """Fill in sources that are down right now with their last saved copy.

    For each failed panel source, look up the newest stored reading for
    the same break and source. If one exists, replace the failed result
    with that stored data, marked stored=True so the page can say
    "showing saved copy from <time>" instead of "unavailable".
    Never raises: if the database itself is down, the panel is returned
    unchanged.
    """
    failed_slugs = [
        meta["slug"] for key, meta in PANEL_SOURCES.items()
        if panel.get(key) and not panel[key].get("live")
    ]
    if not failed_slugs:
        return panel

    try:
        for slug in failed_slugs:
            reading = db.session.execute(
                select(Reading)
                .filter_by(break_id=break_id, source=slug)
                .filter(Reading.data_json.is_not(None))
                .order_by(Reading.retrieved_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            if reading is None:
                continue
            key = PANEL_KEY_BY_SLUG[slug]
            panel[key] = {
                "live": True,
                "stored": True,
                "stored_at": reading.retrieved_at,
                "reading_id": reading.id,
                "source": panel[key].get("source"),
                "data": reading.data_json,
                "fetched_at": reading.retrieved_at.isoformat(),
                "error": panel[key].get("error"),
            }
    except SQLAlchemyError:
        db.session.rollback()
        log.exception("Could not load stored fallbacks")
    return panel
