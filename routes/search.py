"""Search pages (A4). Routes only parse the request, call search_service, render."""

import uuid

from flask import current_app, render_template, request, session, url_for

from models.reading import KINDS
from services.breaks_service import load_breaks
from services.search_service import (
    SORTS,
    describe_filters,
    log_search,
    recent_events,
    run_search,
)
from services.source_registry import ALLOWED_SOURCES, SOURCE_LABELS


def search_session_id():
    """A random id for this browser (no personal data), kept in the session cookie."""
    return session.setdefault("search_sid", uuid.uuid4().hex)


def register_search_routes(app):
    @app.route("/search")
    def search():
        breaks = load_breaks(current_app.config["DATA_DIR"])
        breaks_by_id = {b["id"]: b for b in breaks}
        result = run_search(request.args, breaks, per_page=current_app.config["SEARCH_PER_PAGE"])

        # Pager links carry `se` (the event id), so a page turn is not a new search.
        event_id = request.args.get("se", type=int)
        if event_id is None and result["state"] in ("results", "empty"):
            event_id = log_search(result, search_session_id())

        params = result["params"]
        chips = [
            (label, url_for("search", **{k: v for k, v in params.items() if k != key}))
            for key, label in describe_filters(result["filters"], breaks_by_id).items()
        ]
        return render_template(
            "search.html",
            **result,
            event_id=event_id,
            chips=chips,
            breaks=breaks_by_id,
            sources=ALLOWED_SOURCES,
            source_labels=SOURCE_LABELS,
            kinds=KINDS,
            sorts=SORTS,
        ), (503 if result["state"] == "error" else 200)

    @app.route("/search/history")
    def search_history():
        events, totals = recent_events()
        return render_template(
            "search_history.html",
            events=events,
            totals=totals,
            breaks={b["id"]: b for b in load_breaks(current_app.config["DATA_DIR"])},
            source_labels=SOURCE_LABELS,
        )
