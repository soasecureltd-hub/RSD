"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field
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


# ============ Camera Health Schemas ============

class CameraMetrics(BaseModel):
    blur_score: float
    brightness: float
    contrast: float
    noise_level: float
    fps: float


class DetectionObject(BaseModel):
    """Detected object in frame"""
    class_: str = Field(alias="class")
    confidence: float
    box: List[float]  # [x1, y1, x2, y2]
    
    class Config:
        populate_by_name = True


class CameraHealthInput(BaseModel):
    camera_id: str
    frame_data: str  # Base64 encoded image


class CameraHealthResponse(BaseModel):
    camera_id: str
    health_score: float
    metrics: CameraMetrics
    issues: List[str]
    status: str
    timestamp: datetime
    detections: List[Dict] = Field(default=[])  # List of detected objects
    object_counts: Dict[str, int] = Field(default={})  # Count by class
    detection_enabled: bool = Field(default=False)


# ============ AI Prediction Schemas ============

class AIPredictionResponse(BaseModel):
    unauthorized_access: float
    insider_threat: float
    emergency_failure: float
    perimeter_breach: float
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


class AnomalyDetectionResponse(BaseModel):
    total_anomalies: int
    anomalies: List[AnomalyAlert]
    status: str

