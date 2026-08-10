"""Application configuration — loads from .env with sensible defaults."""

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


class Settings:
    # App
    APP_NAME: str = "Polelo"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    SECRET_KEY: str = os.getenv("JWT_SECRET", "polelo-dev-secret-change-in-production")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    DB_POOL_MIN: int = int(os.getenv("DB_POOL_MIN", "1"))
    DB_POOL_MAX: int = int(os.getenv("DB_POOL_MAX", "10"))

    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")

    # MQTT
    MQTT_BROKER: str = os.getenv("MQTT_BROKER", "localhost")
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", "1883"))

    # S3 / MinIO
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT", "http://localhost:9000")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "minioadmin")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "minioadmin")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "polelo-snapshots")

    # CORS
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # Rate limiting (requests per minute per role)
    RATE_LIMIT_LEARNER: int = int(os.getenv("RATE_LIMIT_LEARNER", "60"))
    RATE_LIMIT_TRANSLATOR: int = int(os.getenv("RATE_LIMIT_TRANSLATOR", "120"))
    RATE_LIMIT_REVIEWER: int = int(os.getenv("RATE_LIMIT_REVIEWER", "120"))
    RATE_LIMIT_TEACHER: int = int(os.getenv("RATE_LIMIT_TEACHER", "120"))
    RATE_LIMIT_ADMIN: int = int(os.getenv("RATE_LIMIT_ADMIN", "300"))

    # API keys for internal AI workers
    API_KEY_HEADER: str = "X-API-Key"
    API_KEYS: list[str] = [
        k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()
    ]

    # Moodle integration
    MOODLE_API_KEYS: list[str] = [
        k.strip() for k in os.getenv("MOODLE_API_KEYS", "").split(",") if k.strip()
    ]
    MOODLE_API_KEY = os.getenv("MoodleApiKey", "")
    MOODLE_LTI_SECRET = os.getenv("MoodleLtiSecret", "")
    MOODLE_WEBHOOK_SECRET: list[str] = [
        k.strip() for k in os.getenv("MoodleWebhookSecret", "").split(",") if k.strip()
    ]

    # Embedded widgets
    EMBED_BASE_URL: str = os.getenv("EMBED_BASE_URL", "")
    # Origins allowed to frame the /embed/* pages (space/comma separated or "*")
    EMBED_ALLOWED_ORIGINS: str = os.getenv("EMBED_ALLOWED_ORIGINS", "*")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")


settings = Settings()
