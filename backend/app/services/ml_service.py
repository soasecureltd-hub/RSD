"""
ML service for risk predictions using scikit-learn.

Uses a MultiOutputClassifier(LogisticRegression) pipeline trained on synthetic data
derived from security assessment domain knowledge. If a saved model exists at
MODEL_PATH it is loaded; otherwise a new model is trained and saved automatically.
"""
import numpy as np
import joblib
from pathlib import Path
from typing import Dict
from app.config import settings

FEATURE_NAMES = [
    "overall_score",
    "physical_security_score",
    "access_control_score",
    "personnel_score",
    "incident_history_score",
    "emergency_preparedness_score",
]

TARGET_NAMES = [
    "unauthorized_access",
    "insider_threat",
    "emergency_failure",
    "perimeter_breach",
]

_model = None  # module-level singleton


def _generate_training_data(n: int = 800):
    """
    Generate synthetic training data.
    Higher score = higher risk (Poor=90, Excellent=10 in this system).
    """
    rng = np.random.default_rng(42)
    X = rng.uniform(10, 90, size=(n, len(FEATURE_NAMES)))
    noise = rng.normal(0, 5, size=(n, 4))

    physical  = X[:, 1]
    access    = X[:, 2]
    personnel = X[:, 3]
    emergency = X[:, 5]

    y = np.column_stack([
        (access    + noise[:, 0] > 55).astype(int),  # unauthorized_access
        (personnel + noise[:, 1] > 55).astype(int),  # insider_threat
        (emergency + noise[:, 2] > 55).astype(int),  # emergency_failure
        (physical  + noise[:, 3] > 55).astype(int),  # perimeter_breach
    ])
    return X.astype(np.float32), y


def _train_and_save() -> object:
    """Train a logistic regression pipeline on synthetic data and persist it."""
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.multioutput import MultiOutputClassifier

    X, y = _generate_training_data()
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", MultiOutputClassifier(LogisticRegression(max_iter=500, random_state=42))),
    ])
    pipeline.fit(X, y)

    model_path = Path(settings.MODEL_PATH)
    joblib.dump(pipeline, model_path)
    print(f"[ml_service] Model trained and saved to {model_path}")
    return pipeline


def _get_model():
    """Lazy-load or train the singleton model."""
    global _model
    if _model is not None:
        return _model
    model_path = Path(settings.MODEL_PATH)
    if model_path.exists():
        _model = joblib.load(model_path)
        print(f"[ml_service] Model loaded from {model_path}")
    else:
        _model = _train_and_save()
    return _model


def predict(assessment_data: Dict) -> Dict:
    """
    Predict risk probabilities from an assessment's computed scores.

    Args:
        assessment_data: dict with keys:
            - overall_score (float)
            - category_scores (dict): keys are category names, values are floats

    Returns:
        dict with keys: unauthorized_access, insider_threat, emergency_failure, perimeter_breach
        Each value is a float in [0, 1] representing the probability of that risk.
    """
    model = _get_model()
    cat = assessment_data.get("category_scores", {})
    features = np.array([[
        assessment_data.get("overall_score", 50.0),
        cat.get("Physical Security", 50.0),
        cat.get("Access Control", 50.0),
        cat.get("Personnel", 50.0),
        cat.get("Incident History", 50.0),
        cat.get("Emergency Preparedness", 50.0),
    ]], dtype=np.float32)

    # MultiOutputClassifier.predict_proba returns a list of arrays,
    # one per target. Each array has shape (n_samples, n_classes).
    # We want P(class=1) for sample 0.
    probas = model.predict_proba(features)
    return {
        TARGET_NAMES[i]: round(float(probas[i][0][1]), 3)
        for i in range(len(TARGET_NAMES))
    }
