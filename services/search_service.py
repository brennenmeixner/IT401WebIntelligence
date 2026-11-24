"""Keyword search over saved readings (A4).

Retrieve -> Filter -> Rank -> Paginate, all inside one SQL query, so the
database does the work and only one page of rows is ever loaded.

- normalize_query(): tidy the raw text into tokens (Manning: tokenization +
  normalization). No stop-word removal, stemming or synonyms on purpose.
- parse_filters() / parse_sort() / parse_page(): check every URL value
  against an allowed set; bad values are ignored with a notice, never a 500.
- build_statement(): one SELECT with keyword matching (AND across tokens,
  OR across fields), the filters, and an ORDER BY with a relevance score.
- run_search(): ties it together for the route and handles DB failure.
- log_search() / record_selection() / recent_events(): search telemetry.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models.reading import KINDS, Reading, utc_now
from models.search_event import SearchEvent
from services.source_registry import ALLOWED_SOURCES, SOURCE_LABELS

log = logging.getLogger(__name__)

MAX_QUERY = 100
RECENT_HOURS = 48
SORTS = {
    "relevance": "Best match",
    "newest": "Newest first",
    "oldest": "Oldest first",
    "title": "Title A to Z",
}
FILTER_KEYS = ("break_id", "source", "kind", "date_from", "date_to")


# ---------------------------------------------------------------------------
# Query processing
# ---------------------------------------------------------------------------

def normalize_query(raw):
    """Turn raw search text into {raw, normalized, tokens, truncated}.

    Collapses all whitespace to single spaces, caps the length at MAX_QUERY,
    and casefolds for matching. `raw` keeps what the user typed (trimmed)
    so the search box and telemetry show their own words.
    """
    raw = (raw or "").strip()
    collapsed = " ".join(raw.split())
    truncated = len(collapsed) > MAX_QUERY
    normalized = collapsed[:MAX_QUERY].strip().casefold()
    return {"raw": raw, "normalized": normalized, "tokens": normalized.split(), "truncated": truncated}


def escape_like(text):
    """Escape LIKE wildcards so '100%' or 'a_b' match those literal characters."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _contains(column, text):
    return column.ilike(f"%{escape_like(text)}%", escape="\\")


# ---------------------------------------------------------------------------
# Parsing URL parameters
# ---------------------------------------------------------------------------

def _parse_date(text):
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_filters(args, break_ids):
    """Validate the filter values from the URL.

    Returns (filters, notices). `filters` holds only accepted values, as the
    strings that go back into links. Unknown values are dropped with a notice.
    """
    filters, notices = {}, []
    allowed = {"break_id": set(break_ids), "source": set(ALLOWED_SOURCES), "kind": set(KINDS)}
    for key, values in allowed.items():
        value = (args.get(key) or "").strip()
        if not value:
            continue
        if value in values:
            filters[key] = value
        else:
            notices.append(f"Ignored unknown filter value '{value[:40]}'.")

    dates = {}
    for key in ("date_from", "date_to"):
        value = (args.get(key) or "").strip()
        if not value:
            continue
        parsed = _parse_date(value)
        if parsed is None:
            notices.append(f"Ignored '{value[:20]}': dates must look like 2026-11-09.")
        else:
            dates[key] = parsed
    if len(dates) == 2 and dates["date_from"] > dates["date_to"]:
        notices.append("Ignored the date range: the start date is after the end date.")
        dates = {}
    filters.update({key: d.isoformat() for key, d in dates.items()})
    return filters, notices


def parse_sort(value, has_keyword):
    """Whitelist the sort; the default is best match with a keyword, else newest."""
    if value in SORTS and (value != "relevance" or has_keyword):
        return value
    return "relevance" if has_keyword else "newest"


def parse_page(value):
    """Return (page, notice). Anything that isn't a whole number >= 1 becomes page 1."""
    try:
        page = int(value or 1)
    except (TypeError, ValueError):
        return 1, f"'{str(value)[:20]}' isn't a page number, so this is page 1."
    if page < 1:
        return 1, "Page numbers start at 1, so this is page 1."
    return page, None


# ---------------------------------------------------------------------------
# The SQL statement
# ---------------------------------------------------------------------------

def _break_ids_matching(token, breaks):
    """Ids of breaks whose name contains the token (breaks live in JSON, not SQL)."""
    return [b["id"] for b in breaks if token in b.get("name", "").casefold()]


def build_statement(query, filters, sort, breaks, now=None):
    """One SELECT: keyword match, filters, then ORDER BY (relevance or a field).

    Keyword rule: every token must appear in the title, the description, or
    the break's name (AND across tokens, OR across fields).
    Relevance score per row (see README "Retrieval Strategy"):
      +5 the whole query is the exact title
      +3 per token found in the title
      +1 per token found in the description
      +1 retrieved in the last RECENT_HOURS hours
    Ties go to the newest reading, then the highest id, so pages are stable.
    """
    now = now or utc_now()
    stmt = select(Reading)

    score = case((func.lower(Reading.title) == query["normalized"], 5), else_=0)
    for token in query["tokens"]:
        fields = [_contains(Reading.title, token), _contains(Reading.description, token)]
        break_ids = _break_ids_matching(token, breaks)
        if break_ids:
            fields.append(Reading.break_id.in_(break_ids))
        stmt = stmt.where(or_(*fields))
        score = score + case((fields[0], 3), else_=0) + case((fields[1], 1), else_=0)
    score = score + case((Reading.retrieved_at >= now - timedelta(hours=RECENT_HOURS), 1), else_=0)

    for key in ("break_id", "source", "kind"):
        if key in filters:
            stmt = stmt.where(getattr(Reading, key) == filters[key])
    if "date_from" in filters:
        stmt = stmt.where(Reading.retrieved_at >= datetime.fromisoformat(filters["date_from"]))
    if "date_to" in filters:
        # "to" includes that whole day.
        stmt = stmt.where(Reading.retrieved_at < datetime.fromisoformat(filters["date_to"]) + timedelta(days=1))

    order = {
        "relevance": (score.desc(), Reading.retrieved_at.desc(), Reading.id.desc()),
        "newest": (Reading.retrieved_at.desc(), Reading.id.desc()),
        "oldest": (Reading.retrieved_at.asc(), Reading.id.asc()),
        "title": (Reading.title.asc(), Reading.id.asc()),
    }[sort]
    return stmt.order_by(*order)


# ---------------------------------------------------------------------------
# Running a search
# ---------------------------------------------------------------------------

def run_search(args, breaks, per_page=10, now=None):
    """Parse the URL values, run the search, and describe the page state.

    Returns a dict for the template. `state` is one of: "before" (nothing
    typed or picked), "results", "empty" (no matches), "error" (DB down).
    `params` holds the accepted values, reused for every link on the page.
    """
    query = normalize_query(args.get("q"))
    filters, notices = parse_filters(args, [b["id"] for b in breaks])
    sort = parse_sort(args.get("sort"), bool(query["tokens"]))
    page, page_notice = parse_page(args.get("page"))
    if query["truncated"]:
        notices.append(f"Your search was shortened to {MAX_QUERY} characters.")
    if page_notice:
        notices.append(page_notice)

    params = {"q": query["raw"], **filters, "sort": sort}
    result = {"query": query, "filters": filters, "sort": sort, "params": params,
              "notices": notices, "pagination": None, "state": "before"}
    if not query["tokens"] and not filters:
        return result  # nothing to search for yet: no DB call, nothing logged

    try:
        stmt = build_statement(query, filters, sort, breaks, now)
        pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
        if pagination.total and page > pagination.pages:
            notices.append(f"There are only {pagination.pages} page(s), so this is the last one.")
            pagination = db.paginate(stmt, page=pagination.pages, per_page=per_page, error_out=False)
    except SQLAlchemyError:
        db.session.rollback()
        log.exception("Search failed")
        result["state"] = "error"
        return result

    result["pagination"] = pagination
    result["state"] = "results" if pagination.total else "empty"
    return result


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

def log_search(result, session_id):
    """Store one SearchEvent for a finished search. Returns its id, or None.

    Never raises: a failed telemetry write is rolled back and logged, and
    the search results are shown anyway.
    """
    query = result["query"]
    event = SearchEvent(
        query_raw=query["raw"][:200],
        query_normalized=query["normalized"][:200],
        filters_json=result["filters"] or None,
        sort=result["sort"],
        result_count=result["pagination"].total,
        no_result=result["pagination"].total == 0,
        session_id=session_id,
    )
    try:
        db.session.add(event)
        db.session.commit()
        return event.id
    except SQLAlchemyError:
        db.session.rollback()
        log.exception("Could not record a search event")
        return None


def record_selection(event_id, rank, reading_id, session_id):
    """Note which result was opened from a search. Ignores anything suspicious.

    Only updates an event that exists and belongs to this browser session,
    so a shared link can't rewrite someone else's search history.
    """
    if not session_id or rank is None or rank < 1:
        return
    try:
        event = db.session.get(SearchEvent, event_id)
        if event is None or event.session_id != session_id:
            return
        event.selected_reading_id = reading_id
        event.selected_rank = rank
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        log.exception("Could not record a search selection")


def recent_events(limit=50):
    """Newest search events plus simple totals, for the history page.

    Returns (events, totals), or (None, None) if the database is down.
    """
    try:
        events = list(db.session.execute(
            select(SearchEvent).order_by(SearchEvent.created_at.desc(), SearchEvent.id.desc()).limit(limit)
        ).scalars())
        totals = db.session.execute(select(
            func.count(SearchEvent.id),
            func.count(case((SearchEvent.no_result.is_(True), 1))),
            func.count(SearchEvent.selected_reading_id),
        )).one()
    except SQLAlchemyError:
        db.session.rollback()
        log.exception("Could not load search history")
        return None, None
    return events, {"searches": totals[0], "no_result": totals[1], "selected": totals[2]}


def describe_filters(filters, breaks_by_id):
    """Human labels for active filters, e.g. {'source': 'Source: NOAA NDBC ...'}."""
    labels = {
        "break_id": lambda v: f"Break: {breaks_by_id.get(v, {}).get('name', v)}",
        "source": lambda v: f"Source: {SOURCE_LABELS.get(v, v)}",
        "kind": lambda v: f"Kind: {v}",
        "date_from": lambda v: f"From {v}",
        "date_to": lambda v: f"To {v}",
    }
    return {key: labels[key](value) for key, value in filters.items()}
