import logging
import os

from sqlalchemy.engine import URL

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

log = logging.getLogger(__name__)


def build_database_uri():
    """Build the SQLAlchemy connection URL from DB_* environment variables.

    Uses URL.create() instead of string formatting so special characters
    in the password (@, :, /) are escaped safely. If the MySQL variables are
    not set (e.g. the SSH tunnel isn't configured yet), fall back to a local
    SQLite file in instance/ so the app still starts for development. The
    real app is meant to run on the CI-Keys MySQL database.
    """
    username = os.environ.get("DB_USERNAME")
    host = os.environ.get("DB_HOST")
    name = os.environ.get("DB_NAME")

    if username and host and name:
        return URL.create(
            drivername="mysql+pymysql",
            username=username,
            password=os.environ.get("DB_PASSWORD"),
            host=host,
            port=int(os.environ.get("DB_PORT", "3306")),
            database=name,
            query={"charset": "utf8mb4"},
        )

    log.warning(
        "DB_USERNAME/DB_HOST/DB_NAME not set -- using local SQLite "
        "(instance/crowdsurf-dev.db) instead of MySQL."
    )
    return "sqlite:///" + os.path.join(BASE_DIR, "instance", "crowdsurf-dev.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    DATA_DIR = os.path.join(BASE_DIR, "data")

    # Database (A3). The URI is built once, at import time.
    SQLALCHEMY_DATABASE_URI = build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # The CI-Keys MySQL connection runs through an SSH tunnel, which can
    # drop idle connections. pool_pre_ping tests a connection before using
    # it; pool_recycle replaces connections before the server times them out.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # External API keys. Only read from the environment, never hardcoded.
    RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5-5")

    # NOAA NWS API asks for a descriptive User-Agent identifying the app +
    # a contact per its usage policy.
    NWS_USER_AGENT = os.environ.get(
        "NWS_USER_AGENT", "crowdsurf-it401-student-project"
    )
    EXTERNAL_API_TIMEOUT = int(os.environ.get("EXTERNAL_API_TIMEOUT", "10"))
    # How long a break page's live data is reused before all sources are
    # fetched again (0 = always fetch fresh).
    PANEL_CACHE_SECONDS = int(os.environ.get("PANEL_CACHE_SECONDS", "300"))

    READINGS_PER_PAGE = 20


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestConfig(Config):
    """Used by pytest only: in-memory SQLite, never the real MySQL."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    PANEL_CACHE_SECONDS = 0  # every test sees fresh (mocked) data
    RAPIDAPI_KEY = None
    ANTHROPIC_API_KEY = None


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestConfig,
    "default": DevelopmentConfig,
}
