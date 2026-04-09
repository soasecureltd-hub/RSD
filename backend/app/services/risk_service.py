"""
Risk assessment and scoring business logic
Ported from old risk_ass.py
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple, List


QUAL_MAPPING = {
    "Poor": 90,
    "Fair": 60,
    "Good": 30,
    "Excellent": 10
}

BASELINES = {
    "incident_score": (40, 10),
    "unauthorized_access_score": (35, 10),
    "response_time_score": (60, 15),
    "cctv_uptime": (85, 5),
    "guard_adequacy": (70, 10),
    "after_hours_security": (65, 10)
}


def map_score(value) -> float:
    """Convert qualitative rating to numeric score"""
    if isinstance(value, str):
        return float(QUAL_MAPPING.get(value, 50))
    return float(value)


def compute_scores(data: Dict) -> Tuple[Dict, Dict, float]:
    """
    Compute risk category scores and overall score
    
    Args:
        data: Input assessment data
        
    Returns:
        Tuple of (category_scores, contributions, overall_score)
    """
    weights = {
        "Physical Security": 0.25,
        "Access Control": 0.30,
        "Personnel": 0.15,
        "Incident History": 0.20,
        "Emergency Preparedness": 0.10
    }
    
    category_scores = {}
    contributions = {}
    
    # Process each category
    for cat, items in data.items():
        if isinstance(items, dict):
            item_scores = [map_score(v) for v in items.values()]
        else:
            item_scores = [map_score(items)]
        
        avg_score = sum(item_scores) / len(item_scores) if item_scores else 0
        category_scores[cat] = round(avg_score, 2)
        contributions[cat] = round(avg_score * weights.get(cat, 0), 2)
    
    overall_score = round(sum(contributions.values()), 2)
    return category_scores, contributions, overall_score


def risk_level(score: float) -> Tuple[str, str, str]:
    """
    Determine risk level badge, label, and color
    
    Args:
        score: Overall risk score (0-100)
        
    Returns:
        Tuple of (badge, level, color)
    """
    if score <= 40:
        return ("🟢 LOW RISK", "Low", "#28a745")
    elif score <= 60:
        return ("🟡 MODERATE RISK", "Moderate", "#ffc107")
    elif score <= 80:
        return ("🟠 HIGH RISK", "High", "#fd7e14")
    else:
        return ("🔴 CRITICAL RISK", "Critical", "#dc3545")


def build_ml_features(data: Dict) -> pd.DataFrame:
    """
    Build feature matrix for ML model from assessment data
    
    Args:
        data: Assessment data
        
    Returns:
        DataFrame with ML features
    """
    try:
        physical = data.get("physical_security", {})
        access = data.get("access_control", {})
        personnel = data.get("personnel", {})
        incidents = data.get("incident_history", {})
        emergency = data.get("emergency_preparedness", {})
        
        return pd.DataFrame([{
            "size_employees": 580,
            "daily_visitors": 60,
            "facility_area_sqm": 22000,
            "cctv_coverage_pct": physical.get("cctv_coverage", 75),
            "cctv_functional_pct": physical.get("cctv_functionality", 85),
            "perimeter_cond_num": map_score(physical.get("perimeter_condition", "Good")),
            "recording_sys_num": 30,
            "exterior_light_num": map_score(physical.get("lighting_quality", "Good")),
            "interior_light_num": 70,
            "parking_security": 1,
            "total_guards": 12,
            "guard_to_area_ratio_per_1000sqm": 12 / 22,
            "training_frequency_years": 2,
            "background_check_num": map_score(personnel.get("background_checks", "Good")),
            "turnover_rate_pct": 60,
            "documentation_quality_num": map_score(incidents.get("documentation_quality", "Good")),
            "avg_response_time_min": 12,
            "communication_score": map_score(emergency.get("communication_system", "Good")),
            "emergency_plan_flag": 1 if emergency.get("emergency_plan") != "Poor" else 0,
            "drill_frequency_per_year": 2
        }])
    except Exception as e:
        raise ValueError(f"Error building ML features: {str(e)}")


def build_anomaly_features(data: Dict) -> Dict:
    """Build features for anomaly detection"""
    try:
        incidents = data.get("incident_history", {})
        physical = data.get("physical_security", {})
        access = data.get("access_control", {})
        personnel = data.get("personnel", {})
        
        return {
            "incident_score": incidents.get("incident_severity_score", 40),
            "unauthorized_access_score": incidents.get("incident_type_score", 35),
            "response_time_score": incidents.get("response_time_score", 60),
            "cctv_uptime": physical.get("cctv_functionality", 85),
            "guard_adequacy": personnel.get("guard_count_ratio", 70),
            "after_hours_security": map_score(access.get("after_hours_security", "Good")),
        }
    except Exception as e:
        raise ValueError(f"Error building anomaly features: {str(e)}")


def generate_baseline(feature_name: str, mean: float, std: float, n: int = 30) -> np.ndarray:
    """Generate baseline distribution"""
    return np.random.normal(mean, std, n)


def z_score_anomaly(current: float, baseline: np.ndarray) -> float:
    """Calculate Z-score for anomaly detection"""
    mean = baseline.mean()
    std = baseline.std()
    if std == 0:
        return 0
    return (current - mean) / std


def run_anomaly_engine(data: Dict) -> List[Dict]:
    """
    Detect anomalies in assessment data
    
    Args:
        data: Assessment data
        
    Returns:
        List of anomaly alerts
    """
    features = build_anomaly_features(data)
    alerts = []
    
    for feature, value in features.items():
        mean, std = BASELINES.get(feature, (50, 10))
        baseline = generate_baseline(feature, mean, std)
        z = z_score_anomaly(value, baseline)
        
        if abs(z) >= 2:
            severity = "HIGH"
        elif abs(z) >= 1.3:
            severity = "MEDIUM"
        else:
            continue
        
        alerts.append({
            "feature": feature,
            "severity": severity,
            "z_score": round(z, 2),
            "value": round(value, 2),
            "message": explain_anomaly(feature, value, z)
        })
    
    return alerts


def explain_anomaly(feature: str, value: float, z: float) -> str:
    """Generate human-readable anomaly explanation"""
    explanations = {
        "incident_score": "Incident activity is significantly higher than normal.",
        "unauthorized_access_score": "Unauthorized access attempts exceed historical patterns.",
        "response_time_score": "Security response time deviates from expected standards.",
        "cctv_uptime": "CCTV uptime has dropped below operational reliability levels.",
        "guard_adequacy": "Guard coverage is insufficient compared to facility risk.",
        "after_hours_security": "After-hours security posture is weaker than baseline."
    }
    return explanations.get(feature, "Unusual behavior detected.")
