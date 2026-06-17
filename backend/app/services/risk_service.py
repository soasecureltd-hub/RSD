"""
Risk assessment and scoring business logic.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple


QUAL_MAPPING = {
    "Poor": 90,
    "Fair": 60,
    "Good": 30,
    "Excellent": 10,
}

# Per-feature baseline statistics (mean, std) for z-score anomaly detection.
# Higher score = higher risk in this system (mirrors QUAL_MAPPING).
BASELINES = {
    "incident_score":            (40, 10),
    "unauthorized_access_score": (35, 10),
    "response_time_score":       (60, 15),
    "cctv_uptime":               (85,  5),
    "guard_adequacy":            (70, 10),
    "after_hours_security":      (65, 10),
}

_CATEGORY_KEYS = [
    "Physical Security",
    "Access Control",
    "Personnel",
    "Incident History",
    "Emergency Preparedness",
]

# Cached synthetic baseline for IsolationForest (built once at first use)
_synthetic_baseline: Optional[np.ndarray] = None


# ── Scoring ───────────────────────────────────────────────────────────────────

def map_score(value) -> float:
    if isinstance(value, str):
        return float(QUAL_MAPPING.get(value, 50))
    return float(value)


def compute_scores(data: Dict) -> Tuple[Dict, Dict, float]:
    weights = {
        "Physical Security":      0.25,
        "Access Control":         0.30,
        "Personnel":              0.15,
        "Incident History":       0.20,
        "Emergency Preparedness": 0.10,
    }
    assert abs(sum(weights.values()) - 1.0) < 1e-9

    category_scores: Dict[str, float] = {}
    contributions:   Dict[str, float] = {}

    for cat, items in data.items():
        item_scores = [map_score(v) for v in items.values()] if isinstance(items, dict) else [map_score(items)]
        avg = sum(item_scores) / len(item_scores) if item_scores else 0
        category_scores[cat] = round(avg, 2)
        contributions[cat]   = round(avg * weights.get(cat, 0), 2)

    overall_score = round(sum(contributions.values()), 2)
    return category_scores, contributions, overall_score


def risk_level(score: float) -> Tuple[str, str, str]:
    if score <= 40:
        return ("🟢 LOW RISK",      "Low",      "#28a745")
    elif score <= 60:
        return ("🟡 MODERATE RISK", "Moderate", "#ffc107")
    elif score <= 80:
        return ("🟠 HIGH RISK",     "High",     "#fd7e14")
    else:
        return ("🔴 CRITICAL RISK", "Critical", "#dc3545")


# ── Anomaly feature extraction ────────────────────────────────────────────────

def build_anomaly_features(data: Dict) -> Dict:
    try:
        incidents = data.get("incident_history", {})
        physical  = data.get("physical_security", {})
        access    = data.get("access_control", {})
        personnel = data.get("personnel", {})

        return {
            "incident_score":            incidents.get("incident_severity_score", 40),
            "unauthorized_access_score": incidents.get("incident_type_score", 35),
            "response_time_score":       incidents.get("response_time_score", 60),
            "cctv_uptime":               physical.get("cctv_functionality", 85),
            "guard_adequacy":            personnel.get("guard_count_ratio", 70),
            "after_hours_security":      map_score(access.get("after_hours_security", "Good")),
        }
    except Exception as e:
        raise ValueError(f"Error building anomaly features: {e}")


def _scores_to_vector(category_scores: Dict) -> np.ndarray:
    """Convert a category_scores dict to a consistent 5-dim numpy vector."""
    return np.array(
        [category_scores.get(k, 50.0) for k in _CATEGORY_KEYS],
        dtype=np.float32,
    )


def _get_synthetic_baseline(n: int = 300) -> np.ndarray:
    """
    Build and cache a synthetic baseline covering four facility risk profiles.
    Used as the IsolationForest training set when real history is unavailable.
    """
    global _synthetic_baseline
    if _synthetic_baseline is not None:
        return _synthetic_baseline

    rng = np.random.default_rng(42)
    profiles = [
        (20, 15, 25, 20, 15),  # Low-risk facility
        (45, 50, 40, 45, 40),  # Moderate risk
        (65, 70, 55, 60, 55),  # High risk
        (80, 80, 75, 80, 80),  # Critical risk
    ]
    per = n // len(profiles)
    segments = [
        np.column_stack([
            rng.normal(m, max(m * 0.2, 5), per).clip(10, 90)
            for m in means
        ])
        for means in profiles
    ]
    _synthetic_baseline = np.vstack(segments).astype(np.float32)
    return _synthetic_baseline


# ── Per-feature z-score helpers ───────────────────────────────────────────────

def _feature_baseline(feature_name: str, mean: float, std: float, n: int = 100) -> np.ndarray:
    """
    Generate a per-feature baseline (100 samples, feature-seeded for stability).
    Using a per-feature seed ensures baselines are order-independent.
    """
    seed = hash(feature_name) & 0xFFFFFFFF
    return np.random.default_rng(seed).normal(mean, std, n)


def z_score_anomaly(current: float, baseline: np.ndarray) -> float:
    std = baseline.std()
    return (current - baseline.mean()) / std if std else 0.0


# ── Main anomaly engine ───────────────────────────────────────────────────────

def run_anomaly_engine(
    data: Dict,
    current_category_scores: Optional[Dict] = None,
    historical_category_scores: Optional[List[Dict]] = None,
) -> Dict:
    """
    Detect anomalies using per-feature Z-scores and multivariate IsolationForest.

    Args:
        data:                      Raw assessment input_data (for per-feature analysis).
        current_category_scores:   Computed category scores for this assessment.
        historical_category_scores: Past assessments' category_scores — when ≥5 are
                                   supplied these replace the synthetic baseline.

    Returns:
        {
            "alerts":               List[Dict],  # per-feature anomaly alerts
            "multivariate_anomaly": bool,         # IsolationForest global flag
            "anomaly_score":        float,        # 0–1, higher = more anomalous
        }
    """
    from sklearn.ensemble import IsolationForest

    features = build_anomaly_features(data)
    alerts: List[Dict] = []

    # ── Per-feature Z-score analysis ──────────────────────────────────────────
    for feature, value in features.items():
        mean, std = BASELINES.get(feature, (50, 10))
        baseline  = _feature_baseline(feature, mean, std)
        z         = z_score_anomaly(value, baseline)

        if abs(z) >= 2.0:
            severity = "HIGH"
        elif abs(z) >= 1.5:
            severity = "MEDIUM"
        else:
            continue

        b_mean = float(baseline.mean())
        alerts.append({
            "feature":           feature,
            "severity":          severity,
            "z_score":           round(z, 2),
            "value":             round(value, 2),
            "baseline_mean":     round(b_mean, 2),
            "direction":         "above" if z > 0 else "below",
            "percent_deviation": round(abs(value - b_mean) / b_mean * 100, 1) if b_mean else 0.0,
            "message":           _explain_anomaly(feature, value, z),
        })

    # ── Multivariate IsolationForest ──────────────────────────────────────────
    multivariate_anomaly = False
    anomaly_score = 0.0

    if current_category_scores:
        has_real_history = historical_category_scores and len(historical_category_scores) >= 5
        baseline_matrix = (
            np.array([_scores_to_vector(s) for s in historical_category_scores])
            if has_real_history
            else _get_synthetic_baseline()
        )

        iso = IsolationForest(contamination=0.1, random_state=42, n_estimators=100)
        iso.fit(baseline_matrix)

        current_vec = _scores_to_vector(current_category_scores).reshape(1, -1)
        multivariate_anomaly = iso.predict(current_vec)[0] == -1

        # score_samples returns negative of anomaly score; negate → higher = worse
        raw = float(-iso.score_samples(current_vec)[0])
        # Typical range is 0.3–0.7; normalise to [0, 1]
        anomaly_score = round(min(max((raw - 0.3) / 0.4, 0.0), 1.0), 3)

    return {
        "alerts":               alerts,
        "multivariate_anomaly": multivariate_anomaly,
        "anomaly_score":        anomaly_score,
    }


# ── Risk velocity ─────────────────────────────────────────────────────────────

def compute_risk_velocity(
    current_scores:  Dict,
    current_overall: float,
    previous_scores: Dict,
    previous_overall: float,
) -> Dict:
    """
    Compute rate of change between two consecutive assessments.
    Flags categories that shifted ≥10 points and overall movement direction.
    """
    category_changes: Dict = {}
    for cat in _CATEGORY_KEYS:
        curr = current_scores.get(cat)
        prev = previous_scores.get(cat)
        if curr is None or prev is None:
            continue
        delta = curr - prev
        if abs(delta) >= 10:
            category_changes[cat] = {
                "delta":     round(delta, 1),
                "direction": "worsened" if delta > 0 else "improved",
                "previous":  round(prev, 1),
                "current":   round(curr, 1),
            }

    overall_delta = current_overall - previous_overall
    return {
        "overall_delta":     round(overall_delta, 2),
        "direction":         "worsening" if overall_delta > 0 else "improving",
        "category_changes":  category_changes,
        "significant":       abs(overall_delta) >= 10 or bool(category_changes),
    }


# ── Anomaly explanation ───────────────────────────────────────────────────────

def _explain_anomaly(feature: str, value: float, z: float) -> str:
    magnitude = "significantly" if abs(z) >= 2 else "notably"
    above = z > 0

    explanations = {
        "incident_score": (
            f"Incident severity is {magnitude} {'elevated' if above else 'below'} baseline ({z:+.1f}σ). "
            + ("Review incident response protocols." if above else "Verify incident reporting is active.")
        ),
        "unauthorized_access_score": (
            f"Unauthorized access indicator is {magnitude} {'high' if above else 'low'} ({z:+.1f}σ). "
            + ("Potential active intrusion risk — investigate access logs." if above else "Verify access monitoring systems are recording.")
        ),
        "response_time_score": (
            f"Response time is {magnitude} {'slower' if above else 'faster'} than expected ({z:+.1f}σ). "
            + ("Review staffing levels and escalation procedures." if above else "Verify timing measurement accuracy.")
        ),
        "cctv_uptime": (
            f"CCTV operational metric is {magnitude} {'above' if above else 'below'} baseline ({z:+.1f}σ). "
            + ("Check for anomalous sensor readings." if above else "Cameras may be offline, degraded, or obstructed.")
        ),
        "guard_adequacy": (
            f"Guard coverage ratio is {magnitude} {'above' if above else 'below'} requirement ({z:+.1f}σ). "
            + ("Verify headcount data accuracy." if above else "Understaffing creates vulnerability windows.")
        ),
        "after_hours_security": (
            f"After-hours security score is {magnitude} {'elevated' if above else 'below'} baseline ({z:+.1f}σ). "
            + ("Review night-time coverage protocols." if above else "Verify shift scheduling data.")
        ),
    }
    return explanations.get(feature, f"Anomalous reading detected ({z:+.1f}σ from baseline).")
