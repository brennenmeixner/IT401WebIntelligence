"""The Reading model: one saved snapshot of one source for one break.

Required A3 fields: id, title, description, source, source_url,
retrieved_at, created_at. Extra fields (justified in the README):
external_id, break_id, kind, data_json, updated_at.
"""

from datetime import datetime, timezone

from extensions import db

# kind values. "summary" is an AI-generated summary built from other readings.
KIND_FORECAST = "forecast"
KIND_OBSERVATION = "observation"
KIND_NOTE = "note"
KIND_SUMMARY = "summary"
KINDS = (KIND_FORECAST, KIND_OBSERVATION, KIND_NOTE, KIND_SUMMARY)


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Reading(db.Model):
    __tablename__ = "readings"
    # Two layers of duplicate protection: the app checks first, and this
    # constraint stops a duplicate even if that check is skipped or two
    # requests race each other.
    __table_args__ = (
        db.UniqueConstraint("source", "external_id", name="uq_reading_source_external_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Provenance: where this came from and when it was fetched.
    source = db.Column(db.String(64), nullable=False, index=True)
    source_url = db.Column(db.String(500), nullable=True)
    external_id = db.Column(db.String(120), nullable=False)
    retrieved_at = db.Column(db.DateTime, nullable=False)

    # Timestamps set by the app (stored as naive UTC).
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=utc_now)

    # Domain fields.
    break_id = db.Column(db.String(50), nullable=False, index=True)
    kind = db.Column(db.String(20), nullable=False, default=KIND_FORECAST)
    data_json = db.Column(db.JSON, nullable=True)

    def __repr__(self):
        return f"<Reading {self.id} {self.source} {self.external_id}>"
