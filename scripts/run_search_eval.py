"""Search evaluation (A4): run each query in docs/eval_queries.json against
the real database and compare the results with the records Brennen marked
as relevant ("expected": reading ids, chosen BEFORE looking at the output).

Usage (SSH tunnel open, from the repo root):
    python scripts/run_search_eval.py

Prints, per query: returned ids by rank, hits, false positives in the top
10, missed relevant records, precision@10 and recall. Not part of pytest:
it needs the real MySQL data.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from services.breaks_service import load_breaks  # noqa: E402
from services.search_service import build_statement, normalize_query, parse_filters, parse_sort  # noqa: E402

TOP_K = 10


def evaluate(case, breaks):
    query = normalize_query(case["query"])
    filters, _ = parse_filters(case.get("filters", {}), [b["id"] for b in breaks])
    stmt = build_statement(query, filters, parse_sort("relevance", bool(query["tokens"])), breaks)
    returned = [r.id for r in db.session.execute(stmt).scalars()]
    expected = set(case["expected"])
    top = returned[:TOP_K]
    hits = [i for i in top if i in expected]
    precision = len(hits) / len(top) if top else 0.0
    recall = len(expected & set(returned)) / len(expected) if expected else 0.0
    return {
        "query": case["query"], "filters": filters, "total": len(returned),
        "top_ids": top, "hits_top": hits,
        "false_positives_top": [i for i in top if i not in expected],
        "missed": sorted(expected - set(returned)),
        "first_relevant_rank": next((n for n, i in enumerate(returned, 1) if i in expected), None),
        "precision_at_10": round(precision, 2), "recall": round(recall, 2),
    }


def main():
    path = os.path.join(os.path.dirname(__file__), "..", "docs", "eval_queries.json")
    with open(path, encoding="utf-8") as f:
        cases = json.load(f)
    app = create_app()
    with app.app_context():
        breaks = load_breaks(app.config["DATA_DIR"])
        for case in cases:
            if not case["expected"]:
                print(f"! '{case['query']}': no expected ids yet; fill them in before trusting precision/recall")
            r = evaluate(case, breaks)
            print(f"\n## {r['query']!r} filters={r['filters']}  ({r['total']} results)")
            print(f"top {TOP_K} ids by rank: {r['top_ids']}")
            print(f"relevant in top {TOP_K}: {r['hits_top']}   false positives: {r['false_positives_top']}")
            print(f"missed relevant: {r['missed']}   first relevant at rank: {r['first_relevant_rank']}")
            print(f"precision@{TOP_K} = {r['precision_at_10']}   recall = {r['recall']}")


if __name__ == "__main__":
    main()
