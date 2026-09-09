BASE_FEE = 20
PER_REPORT_CREDIT = 1
DAYS_IN_MONTH = 30

# Placeholder until survey submissions are stored (later module) — see security.md.
REPORTS_FILED = 18


def compute_statement(reports_filed=REPORTS_FILED):
    """Turn a count of reporting days into the month's rewards statement.

    Credit is capped at the base fee (never a cash payout) and reports_filed
    is clamped to a sane 0..DAYS_IN_MONTH range in case of bad input.
    """
    reports_filed = max(0, min(int(reports_filed or 0), DAYS_IN_MONTH))
    credit = min(BASE_FEE, reports_filed * PER_REPORT_CREDIT)
    due = BASE_FEE - credit

    days = [
        {"n": i + 1, "reported": i < reports_filed}
        for i in range(DAYS_IN_MONTH)
    ]

    return {
        "base_fee": BASE_FEE,
        "per_report": PER_REPORT_CREDIT,
        "reports_filed": reports_filed,
        "credit": credit,
        "due": due,
        "refund_pct": round((credit / BASE_FEE) * 100),
        "bar_width_pct": (credit / BASE_FEE) * 100,
        "is_full_refund": credit >= BASE_FEE,
        "days": days,
    }
