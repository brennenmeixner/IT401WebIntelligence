from flask import current_app, render_template, request

from services.breaks_service import ALL_REGIONS, ANY_WIND, filter_breaks, load_breaks
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
