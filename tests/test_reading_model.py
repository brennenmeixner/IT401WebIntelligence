from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from models.reading import Reading


def make_reading(**overrides):
    fields = {
        "title": "South Jetty: Open-Meteo Marine",
        "source": "open-meteo-marine",
        "external_id": "south-jetty:open-meteo-marine:20260101T00",
        "retrieved_at": datetime(2026, 1, 1, 0, 0),
        "break_id": "south-jetty",
    }
    fields.update(overrides)
    return Reading(**fields)


def test_created_at_is_set_automatically(db):
    reading = make_reading()
    db.session.add(reading)
    db.session.commit()
    assert reading.id is not None
    assert reading.created_at is not None
    assert reading.kind == "forecast"


def test_title_is_required(db):
    db.session.add(make_reading(title=None))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_source_plus_external_id_must_be_unique(db):
    db.session.add(make_reading())
    db.session.commit()
    db.session.add(make_reading(title="a copy"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_same_external_id_from_a_different_source_is_allowed(db):
    db.session.add(make_reading())
    db.session.add(make_reading(source="noaa-nws-forecast"))
    db.session.commit()
    assert db.session.query(Reading).count() == 2
