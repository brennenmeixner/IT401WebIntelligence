"""The SearchEvent model: one row per completed search (A4 telemetry).

Records what was searched, how, and how many results came back, plus which
result (if any) the user then opened. No personal data: session_id is a
random UUID kept in the Flask session cookie, not a login or IP address.
"""

from extensions import db
from models.reading import utc_now


class SearchEvent(db.Model):
    __tablename__ = "search_events"

    id = db.Column(db.Integer, primary_key=True)
    query_raw = db.Column(db.String(200), nullable=False, default="")
    query_normalized = db.Column(db.String(200), nullable=False, default="")
    filters_json = db.Column(db.JSON, nullable=True)
    sort = db.Column(db.String(30), nullable=False)
    result_count = db.Column(db.Integer, nullable=False)
    no_result = db.Column(db.Boolean, nullable=False, default=False)
    session_id = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)

    # Filled in when the user opens a result from this search.
    selected_reading_id = db.Column(db.Integer, db.ForeignKey("readings.id", ondelete="SET NULL"), nullable=True)
    selected_rank = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f"<SearchEvent {self.id} {self.query_normalized!r} {self.result_count}>"
