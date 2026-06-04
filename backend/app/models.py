"""
Database models using SQLAlchemy ORM
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, Boolean, ForeignKey
from datetime import datetime, timezone
from app.db import Base


class User(Base):
    """Application user"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Assessment(Base):
    """Risk Assessment record"""
    __tablename__ = "assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)  # owner
    facility_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Input data
    input_data = Column(JSON, nullable=False)  # The raw form data
    
    # Results
    category_scores = Column(JSON, nullable=True)  # Dict of category -> score
    contributions = Column(JSON, nullable=True)    # Weighted contributions
    overall_score = Column(Float, nullable=True)   # Final risk score
    risk_level = Column(String, nullable=True)     # LOW, MODERATE, HIGH, CRITICAL
    
    # Additional
    notes = Column(Text, nullable=True)


class CameraHealth(Base):
    """Camera health monitoring record"""
    __tablename__ = "camera_health"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Metrics
    health_score = Column(Float, nullable=False)
    blur_score = Column(Float, nullable=True)
    brightness = Column(Float, nullable=True)
    contrast = Column(Float, nullable=True)
    noise_level = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)
    
    # Issues
    issues = Column(JSON, nullable=True)  # List of detected issues
    

class AIPrediction(Base):
    """AI model prediction record"""
    __tablename__ = "ai_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Input features
    input_features = Column(JSON, nullable=False)
    
    # Predictions
    unauthorized_access_prob = Column(Float, nullable=True)
    insider_threat_prob = Column(Float, nullable=True)
    emergency_failure_prob = Column(Float, nullable=True)
    perimeter_breach_prob = Column(Float, nullable=True)
    
    # Explanations
    shap_values = Column(JSON, nullable=True)
