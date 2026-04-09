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
    
    # ML Model
    MODEL_PATH: str = "security_multiorg_model.pkl"
    
    # CORS
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
