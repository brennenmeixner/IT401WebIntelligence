from flask import abort, current_app, flash, redirect, render_template, request, url_for

from services.ai_service import generate_break_summary, latest_summary
from services.breaks_service import ALL_REGIONS, ANY_WIND, filter_breaks, find_break, load_breaks
from services.forecast_service import build_break_panel
from services.reading_service import count_readings, save_panel_snapshot, stored_fallbacks
from services.rewards_service import compute_statement

REGIONS = [ALL_REGIONS, "Ventura County", "Santa Barbara County"]
WINDS = [ANY_WIND, "Offshore", "Onshore", "Cross-shore", "Glassy"]


def _find_break_or_404(break_id):
    match = find_break(load_breaks(current_app.config["DATA_DIR"]), break_id)
    if match is None:
        abort(404)
    return match


def _fetch_panel(break_record):
    return build_break_panel(
        break_record,
        nws_user_agent=current_app.config["NWS_USER_AGENT"],
        timeout=current_app.config.get("EXTERNAL_API_TIMEOUT", 10),
        rapidapi_key=current_app.config.get("RAPIDAPI_KEY"),
    )


def register_routes(app):
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/explore")
    def explore():
        q = request.args.get("q", "").strip()
        region = request.args.get("region", ALL_REGIONS)
        wind = request.args.get("wind", ANY_WIND)

        breaks = load_breaks(current_app.config["DATA_DIR"])
        results = filter_breaks(breaks, q=q, region=region, wind=wind)

        active_filters = []
        if q:
            active_filters.append(f'q="{q}"')
        if region != ALL_REGIONS:
            active_filters.append(f"region={region}")
        if wind != ANY_WIND:
            active_filters.append(f"wind={wind}")

        return render_template(
            "explore.html",
            results=results,
            total_count=len(breaks),
            q=q,
            region=region,
            wind=wind,
            regions=REGIONS,
            winds=WINDS,
            filter_summary="  ·  ".join(active_filters),
            has_filters=bool(active_filters),
        )

    @app.route("/rewards")
    def rewards():
        statement = compute_statement()
        return render_template("rewards.html", statement=statement)

    @app.route("/break/<break_id>")
    def break_detail(break_id):
        breaks = load_breaks(current_app.config["DATA_DIR"])
        match = find_break(breaks, break_id)
        if match is None:
            return render_template("break_detail.html", not_found=True, break_id=break_id), 404

        panel = _fetch_panel(match)
        # Any source that is down right now falls back to its last saved copy.
        panel = stored_fallbacks(match["id"], panel)
        return render_template(
            "break_detail.html",
            not_found=False,
            summary=latest_summary(match["id"]),
            **panel,
        )

    @app.route("/break/<break_id>/save", methods=["POST"])
    def save_break_snapshot(break_id):
        match = _find_break_or_404(break_id)
        outcome = save_panel_snapshot(match, _fetch_panel(match))
        flash(outcome["message"], "success" if outcome["ok"] else "alert")
        return redirect(url_for("break_detail", break_id=break_id))

    @app.route("/break/<break_id>/summarize", methods=["POST"])
    def summarize_break(break_id):
        match = _find_break_or_404(break_id)
        outcome = generate_break_summary(
            match,
            api_key=current_app.config.get("ANTHROPIC_API_KEY"),
            model=current_app.config["ANTHROPIC_MODEL"],
        )
        flash(outcome.message, "success" if outcome.ok else "alert")
        return redirect(url_for("break_detail", break_id=break_id) + "#ai-summary")

    @app.context_processor
    def inject_reading_count():
        # Lets the nav show how many readings are stored, without each
        # route passing it. Falls back to None if the DB is unreachable.
        def reading_count():
            try:
                return count_readings()
            except Exception:  # noqa: BLE001 -- nav badge must never break a page
                return None
        return {"reading_count": reading_count}
