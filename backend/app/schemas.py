"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, List, Optional
from datetime import datetime


# ============ Risk Assessment Schemas ============

class PhysicalSecurityInput(BaseModel):
    perimeter_condition: str
    cctv_coverage: float
    cctv_functionality: float
    lighting_quality: str
    entry_exit_control: str


class AccessControlInput(BaseModel):
    visitor_management: str
    id_verification: str
    restricted_area_protection: str
    after_hours_security: str


class PersonnelInput(BaseModel):
    guard_count_ratio: float
    training_frequency: str
    background_checks: str
    shift_coverage: str


class IncidentHistoryInput(BaseModel):
    incident_severity_score: float
    incident_type_score: float
    response_time_score: float
    documentation_quality: str


class EmergencyPreparednessInput(BaseModel):
    emergency_plan: str
    drill_frequency: str
    communication_system: str
    staff_readiness: str


class RiskAssessmentInput(BaseModel):
    facility_name: Optional[str] = None
    physical_security: PhysicalSecurityInput
    access_control: AccessControlInput
    personnel: PersonnelInput
    incident_history: IncidentHistoryInput
    emergency_preparedness: EmergencyPreparednessInput


class RiskAssessmentResponse(BaseModel):
    id: int
    facility_name: Optional[str]
    created_at: datetime
    category_scores: Dict[str, float]
    contributions: Dict[str, float]
    overall_score: float
    risk_level: str
    
    class Config:
        from_attributes = True


# ============ Auth Schemas ============

class UserCreate(BaseModel):
    email: EmailStr
    # max_length guards against DoS from hashing very large inputs.
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============ AI Prediction Schemas ============

class AIPredictionResponse(BaseModel):
    unauthorized_access: float
    insider_threat: float
    emergency_failure: float
    perimeter_breach: float
    confidence: float = 0.0
    risk_labels: List[str] = Field(default=[
        "Unauthorized Access",
        "Insider Threat",
        "Emergency Failure",
        "Perimeter Breach"
    ])


# ============ Anomaly Detection Schemas ============

class AnomalyAlert(BaseModel):
    feature: str
    severity: str  # HIGH, MEDIUM
    z_score: float
    value: float
    message: str
    direction: Optional[str] = None           # "above" or "below" baseline
    baseline_mean: Optional[float] = None
    percent_deviation: Optional[float] = None


class AnomalyDetectionResponse(BaseModel):
    total_anomalies: int
    anomalies: List[AnomalyAlert]
    status: str
    multivariate_anomaly: bool = False        # IsolationForest global flag
    anomaly_score: float = 0.0               # 0–1, higher = more anomalous
    risk_velocity: Optional[Dict] = None     # rate of change vs previous assessment

