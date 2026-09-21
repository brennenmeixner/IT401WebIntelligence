from flask import current_app, render_template, request

from services.breaks_service import ALL_REGIONS, ANY_WIND, filter_breaks, find_break, load_breaks
from services.forecast_service import build_break_panel
from services.rewards_service import compute_statement

REGIONS = [ALL_REGIONS, "Ventura County", "Santa Barbara County"]
WINDS = [ANY_WIND, "Offshore", "Onshore", "Cross-shore", "Glassy"]


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

        panel = build_break_panel(
            match,
            nws_user_agent=current_app.config["NWS_USER_AGENT"],
            timeout=current_app.config.get("EXTERNAL_API_TIMEOUT", 10),
        )
        return render_template("break_detail.html", not_found=False, **panel)
