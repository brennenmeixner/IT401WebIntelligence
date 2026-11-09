"""CRUD pages for saved readings (A3).

Routes only parse the request, call reading_service, and render. Create,
update and delete are POST-only and protected by Flask-WTF's CSRF token.
"""

from flask import abort, current_app, flash, redirect, render_template, request, session, url_for

from models.reading import KINDS
from services.breaks_service import load_breaks
from services.reading_service import (
    FORM_KINDS,
    MEASUREMENTS,
    create_manual_reading,
    delete_reading,
    get_reading,
    list_readings,
    update_reading,
    utc_to_local_input,
    validate_reading_form,
)
from services.search_service import record_selection
from services.source_registry import ALLOWED_SOURCES, MANUAL_SOURCE, SOURCE_LABELS


def _breaks_by_id():
    return {b["id"]: b for b in load_breaks(current_app.config["DATA_DIR"])}


def _get_or_404(reading_id):
    reading = get_reading(reading_id)
    if reading is None:
        abort(404)
    return reading


def _form_context(**extra):
    return {
        "breaks": _breaks_by_id(),
        "kinds": FORM_KINDS,
        "measurements": MEASUREMENTS,
        "source_labels": SOURCE_LABELS,
        **extra,
    }


def register_reading_routes(app):
    @app.route("/readings")
    def readings_list():
        page = request.args.get("page", 1, type=int)
        break_id = request.args.get("break_id", "").strip()
        source = request.args.get("source", "").strip()
        kind = request.args.get("kind", "").strip()

        pagination = list_readings(
            page=max(page, 1),
            per_page=current_app.config["READINGS_PER_PAGE"],
            break_id=break_id or None,
            source=source or None,
            kind=kind or None,
        )
        return render_template(
            "readings/list.html",
            pagination=pagination,
            readings=pagination.items,
            breaks=_breaks_by_id(),
            sources=ALLOWED_SOURCES,
            source_labels=SOURCE_LABELS,
            kinds=KINDS,
            filters={"break_id": break_id, "source": source, "kind": kind},
        )

    @app.route("/readings/<int:reading_id>")
    def reading_detail(reading_id):
        reading = _get_or_404(reading_id)
        # Opened from a search result: note which one (telemetry-only write on a GET, see README).
        event_id = request.args.get("se", type=int)
        if event_id is not None:
            record_selection(event_id, request.args.get("rank", type=int), reading.id, session.get("search_sid"))
        return render_template(
            "readings/detail.html",
            reading=reading,
            breaks=_breaks_by_id(),
            source_labels=SOURCE_LABELS,
        )

    @app.route("/readings/new", methods=["GET", "POST"])
    def reading_create():
        if request.method == "GET":
            return render_template(
                "readings/form.html",
                **_form_context(mode="create", values={"break_id": request.args.get("break_id", "")}, errors=[]),
            )

        cleaned, errors = validate_reading_form(request.form, valid_break_ids=_breaks_by_id().keys())
        if errors:
            return render_template(
                "readings/form.html",
                **_form_context(mode="create", values=request.form, errors=errors),
            ), 400

        outcome = create_manual_reading(cleaned)
        if not outcome.ok:
            return render_template(
                "readings/form.html",
                **_form_context(mode="create", values=request.form, errors=[outcome.message]),
            ), outcome.status

        flash(outcome.message, "success")
        return redirect(url_for("reading_detail", reading_id=outcome.reading.id))

    @app.route("/readings/<int:reading_id>/edit", methods=["GET", "POST"])
    def reading_edit(reading_id):
        reading = _get_or_404(reading_id)
        is_manual = reading.source == MANUAL_SOURCE["slug"]

        if request.method == "GET":
            values = {
                "title": reading.title,
                "description": reading.description or "",
                "kind": reading.kind,
                "source_url": reading.source_url or "",
                "retrieved_at": utc_to_local_input(reading.retrieved_at),
            }
            if is_manual and reading.data_json:
                values.update({k: v for k, v in reading.data_json.items() if k in MEASUREMENTS})
            return render_template(
                "readings/form.html",
                **_form_context(mode="edit", reading=reading, is_manual=is_manual, values=values, errors=[]),
            )

        # An AI summary keeps kind="summary"; people can't pick it for other readings.
        allowed_kinds = FORM_KINDS + ((reading.kind,) if reading.kind not in FORM_KINDS else ())
        cleaned, errors = validate_reading_form(
            request.form, valid_break_ids=(), editing=True, allowed_kinds=allowed_kinds
        )
        if errors:
            return render_template(
                "readings/form.html",
                **_form_context(mode="edit", reading=reading, is_manual=is_manual, values=request.form, errors=errors),
            ), 400

        outcome = update_reading(reading, cleaned)
        flash(outcome.message, "success" if outcome.ok else "alert")
        return redirect(url_for("reading_detail", reading_id=reading.id))

    @app.route("/readings/<int:reading_id>/delete", methods=["POST"])
    def reading_delete(reading_id):
        reading = _get_or_404(reading_id)
        outcome = delete_reading(reading)
        flash(outcome.message, "success" if outcome.ok else "alert")
        if not outcome.ok:
            return redirect(url_for("reading_detail", reading_id=reading_id))
        return redirect(url_for("readings_list"))
