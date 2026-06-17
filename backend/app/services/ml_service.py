"""
ML service for risk predictions using scikit-learn.

RandomForest multi-label classifier trained on domain-informed synthetic data
spanning six facility risk archetypes with feature engineering.
"""
import numpy as np
import joblib
import logging
from pathlib import Path
from typing import Dict
from app.config import settings

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "overall_score",
    "physical_security_score",
    "access_control_score",
    "personnel_score",
    "incident_history_score",
    "emergency_preparedness_score",
    "access_x_incident",       # interaction: poor access control + high incidents
    "physical_x_personnel",    # interaction: poor physical security + understaffing
]

TARGET_NAMES = [
    "unauthorized_access",
    "insider_threat",
    "emergency_failure",
    "perimeter_breach",
]

_model = None


def _engineer_features(raw: np.ndarray) -> np.ndarray:
    """
    Add pairwise interaction features to a (n, 6) input array.

    Columns: overall, physical, access, personnel, incident, emergency
    Interactions encode compound risk — e.g. weak access control becomes
    far more dangerous when incident history is also high.
    """
    physical  = raw[:, 1]
    access    = raw[:, 2]
    personnel = raw[:, 3]
    incident  = raw[:, 4]

    # Normalise to [0,1] then scale back so magnitudes stay comparable
    access_x_incident    = (access / 90.0) * (incident / 90.0) * 90.0
    physical_x_personnel = (physical / 90.0) * (personnel / 90.0) * 90.0

    return np.column_stack([raw, access_x_incident, physical_x_personnel])


def _generate_training_data(n: int = 1500):
    """
    Domain-informed synthetic training data across six facility archetypes.

    Higher score = higher risk, matching QUAL_MAPPING (Poor=90, Excellent=10).

    Archetypes (mean_physical, mean_access, mean_personnel, mean_incident, mean_emergency):
      1. Well-secured: all dimensions low-risk
      2. Moderate overall risk
      3. High risk: aging infrastructure
      4. Access/incident failure focus
      5. Personnel + emergency preparedness weak
      6. Critical: every dimension poor
    """
    rng = np.random.default_rng(42)

    archetypes = [
        (20, 15, 25, 20, 15),
        (40, 50, 35, 45, 40),
        (65, 70, 55, 60, 55),
        (25, 75, 65, 70, 30),
        (72, 38, 72, 48, 78),
        (80, 82, 78, 80, 82),
    ]

    per_archetype = n // len(archetypes)
    remainder = n - per_archetype * len(archetypes)
    segments = []

    for i, means in enumerate(archetypes):
        count = per_archetype + (1 if i < remainder else 0)
        stds = tuple(max(m * 0.2, 5) for m in means)
        seg = np.column_stack([
            rng.normal(m, s, count).clip(10, 90)
            for m, s in zip(means, stds)
        ])
        # Weighted average mirrors compute_scores weights
        weights = np.array([0.25, 0.30, 0.15, 0.20, 0.10])
        overall = (seg * weights).sum(axis=1, keepdims=True)
        segments.append(np.hstack([overall, seg]))

    X = np.vstack(segments).astype(np.float32)
    X_eng = _engineer_features(X)
    noise = rng.normal(0, 3, (len(X), 4))

    physical  = X[:, 1]
    access    = X[:, 2]
    personnel = X[:, 3]
    incident  = X[:, 4]
    emergency = X[:, 5]
    overall   = X[:, 0]

    # Labels incorporate interaction effects, not just single-feature thresholds
    y = np.column_stack([
        # Unauthorized access: access control + incident history compound
        ((access + incident * 0.5 + noise[:, 0]) > 58).astype(int),
        # Insider threat: poor personnel quality + lax access control
        ((personnel + access * 0.4 + noise[:, 1]) > 60).astype(int),
        # Emergency failure: preparedness weakness amplified by overall risk
        ((emergency + overall * 0.25 + noise[:, 2]) > 62).astype(int),
        # Perimeter breach: physical security degradation + incident history
        ((physical + incident * 0.4 + noise[:, 3]) > 56).astype(int),
    ])

    return X_eng.astype(np.float32), y


def _train_and_save() -> object:
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.multioutput import MultiOutputClassifier
    from sklearn.model_selection import train_test_split

    X, y = _generate_training_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", MultiOutputClassifier(
            RandomForestClassifier(
                n_estimators=200,
                max_depth=8,
                min_samples_leaf=4,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )
        )),
    ])
    pipeline.fit(X_train, y_train)

    train_acc = pipeline.score(X_train, y_train)
    test_acc  = pipeline.score(X_test,  y_test)
    logger.info("[ml_service] train_acc=%.3f  test_acc=%.3f", train_acc, test_acc)

    model_path = Path(settings.MODEL_PATH)
    joblib.dump(pipeline, model_path)
    logger.info("[ml_service] model saved → %s", model_path)
    return pipeline


def _get_model():
    global _model
    if _model is not None:
        return _model
    model_path = Path(settings.MODEL_PATH)
    if model_path.exists():
        try:
            candidate = joblib.load(model_path)
            # Sanity-check: new model expects 8 features (6 raw + 2 interactions)
            candidate.predict(np.zeros((1, len(FEATURE_NAMES)), dtype=np.float32))
            _model = candidate
            logger.info("[ml_service] model loaded from %s", model_path)
        except Exception:
            logger.warning("[ml_service] cached model incompatible, retraining…")
            _model = _train_and_save()
    else:
        _model = _train_and_save()
    return _model


def predict(assessment_data: Dict) -> Dict:
    """
    Predict threat probabilities from assessment scores.

    Args:
        assessment_data:
            overall_score (float) and category_scores (dict of category → float)

    Returns:
        Dict with keys: unauthorized_access, insider_threat, emergency_failure,
        perimeter_breach (all floats in [0, 1]) and confidence (float in [0, 1]).
    """
    model = _get_model()
    cat = assessment_data.get("category_scores", {})

    raw = np.array([[
        assessment_data.get("overall_score", 50.0),
        cat.get("Physical Security", 50.0),
        cat.get("Access Control", 50.0),
        cat.get("Personnel", 50.0),
        cat.get("Incident History", 50.0),
        cat.get("Emergency Preparedness", 50.0),
    ]], dtype=np.float32)

    features = _engineer_features(raw)

    # MultiOutputClassifier.predict_proba returns list of (n_samples, n_classes) arrays
    probas = model.predict_proba(features)
    predictions = {
        TARGET_NAMES[i]: round(float(probas[i][0][1]), 3)
        for i in range(len(TARGET_NAMES))
    }

    # Confidence: mean distance from the 0.5 decision boundary, scaled to [0, 1]
    predictions["confidence"] = round(
        float(np.mean([abs(v - 0.5) * 2 for v in predictions.values()])), 3
    )

    return predictions
