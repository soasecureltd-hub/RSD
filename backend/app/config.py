"""
Application configuration
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./rsd.db"
    
    # FastAPI
    DEBUG: bool = True
    API_TITLE: str = "Risk-Security Diagnostic API"
    API_VERSION: str = "1.0.0"
    
    # Camera
    CAMERA_HISTORY_SIZE: int = 100
    CAMERA_FRAME_SKIP: int = 3
    YOLO_CONFIDENCE_THRESHOLD: float = 0.5  # Minimum confidence for object detections

    # ML Model
    MODEL_PATH: str = "security_multiorg_model.pkl"

    # Rate limiting
    RATE_LIMIT_CAMERA_ANALYZE: str = "20/minute"  # Max frame submissions per client

    # NOTE: SQLite does not support concurrent writes. If deploying with Gunicorn
    # and multiple workers (--workers > 1), switch DATABASE_URL to PostgreSQL.
    
    # CORS
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # JWT Authentication
    JWT_SECRET_KEY: str = "CHANGE-THIS-SECRET-IN-PRODUCTION-USE-32-CHAR-MINIMUM"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # Sentry
    SENTRY_DSN: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
