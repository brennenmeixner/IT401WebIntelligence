import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    DATA_DIR = os.path.join(BASE_DIR, "data")

    # External API keys / service config
    API_KEY = os.environ.get("API_KEY")
    AI_SERVICE_API_KEY = os.environ.get("AI_SERVICE_API_KEY")

    # NOAA NWS API asks for a descriptive User-Agent identifying the app +
    # a contact per its usage policy. None of the A2 data sources require
    # an API key, so this is the only "credential-like" config value.
    NWS_USER_AGENT = os.environ.get(
        "NWS_USER_AGENT", "crowdsurf-it401-student-project"
    )
    EXTERNAL_API_TIMEOUT = int(os.environ.get("EXTERNAL_API_TIMEOUT", "10"))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
