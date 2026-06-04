"""
Application configuration
"""
import os
import secrets
import warnings
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

# Placeholder shipped in the repo. Treated as "unset" so it can never be used
# as a real signing key in production.
_PLACEHOLDER_SECRET = "CHANGE-THIS-SECRET-IN-PRODUCTION-USE-32-CHAR-MINIMUM"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./rsd.db"

    # FastAPI
    DEBUG: bool = False
    API_TITLE: str = "Risk-Security Diagnostic API"
    API_VERSION: str = "1.0.0"
    
    # Camera
    CAMERA_HISTORY_SIZE: int = 100
    CAMERA_FRAME_SKIP: int = 3
    YOLO_CONFIDENCE_THRESHOLD: float = 0.5  # Minimum confidence for object detections

    # Limits for uploaded frames (guards against decompression-bomb / memory DoS)
    MAX_FRAME_BYTES: int = 8 * 1024 * 1024  # 8 MB decoded image data
    MAX_FRAME_PIXELS: int = 25_000_000  # ~25 MP (e.g. 6000x4000)

    # ML Model
    MODEL_PATH: str = "security_multiorg_model.pkl"

    # Rate limiting
    RATE_LIMIT_CAMERA_ANALYZE: str = "20/minute"  # Max frame submissions per client

    # NOTE: SQLite does not support concurrent writes. If deploying with Gunicorn
    # and multiple workers (--workers > 1), switch DATABASE_URL to PostgreSQL.
    
    # CORS — accepts a JSON array string or a comma-separated string from env.
    # e.g. ALLOWED_ORIGINS=https://foo.onrender.com,https://bar.onrender.com
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # JWT Authentication
    # No usable default: must be supplied via environment / .env in production.
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # Sentry
    SENTRY_DSN: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

    @model_validator(mode="after")
    def _validate_secret(self):
        """Refuse to run with a missing/placeholder JWT secret outside DEBUG.

        In DEBUG we fall back to an ephemeral random secret (tokens won't
        survive a restart, which is fine for local dev). In production this
        is a hard failure so the app never signs tokens with a known key.
        """
        if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY == _PLACEHOLDER_SECRET:
            if self.DEBUG:
                self.JWT_SECRET_KEY = secrets.token_urlsafe(48)
                warnings.warn(
                    "JWT_SECRET_KEY not set; using a random ephemeral secret "
                    "for this DEBUG session. Set JWT_SECRET_KEY in .env.",
                    stacklevel=2,
                )
            else:
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a strong, unique value "
                    "(>=32 chars) when DEBUG is False. Set it in the "
                    "environment or .env file."
                )
        elif len(self.JWT_SECRET_KEY) < 32 and not self.DEBUG:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters.")
        return self


settings = Settings()
