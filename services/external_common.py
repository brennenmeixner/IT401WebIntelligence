"""Shared result shape for every external (API or scraped) data source.

Every service in this package returns this same dict so the orchestrator
(services/forecast_service.py) and templates only ever need to check one
thing: result["live"].
"""

from datetime import datetime, timezone


def live_result(source, data):
    """Build a successful external-source result dict."""
    return {
        "live": True,
        "source": source,
        "data": data,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "error": None,
    }


def failed_result(source, error):
    """Build a failed/unavailable external-source result dict."""
    return {
        "live": False,
        "source": source,
        "data": None,
        "fetched_at": None,
        "error": str(error),
    }
