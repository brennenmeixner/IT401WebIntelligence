import logging
import os

from dotenv import load_dotenv

# Load .env before importing config: Config reads os.environ at import time.
load_dotenv()

from flask import Flask, render_template

import models  # noqa: F401  (registers the SQLAlchemy models with db)
from config import config
from extensions import csrf, db, migrate
from routes.main import register_routes
from routes.readings import register_reading_routes


def register_error_handlers(app):
    """Friendly error pages instead of raw tracebacks."""

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, message="That page or record doesn't exist."), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        app.logger.exception("Unhandled server error")
        return render_template("error.html", code=500, message="Something went wrong on our side."), 500


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    logging.basicConfig(level=logging.INFO)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    register_routes(app)
    register_reading_routes(app)
    register_error_handlers(app)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=app.config.get("DEBUG", False))
