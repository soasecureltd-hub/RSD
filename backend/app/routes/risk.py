"""Risk assessment routes"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas, crud
from app.db import get_db
from app.dependencies import get_current_user
from app.services.risk_service import compute_scores, risk_level, run_anomaly_engine
from app.services.ml_service import predict as ml_predict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.post("/assess", response_model=schemas.RiskAssessmentResponse)
def create_assessment(
    assessment: schemas.RiskAssessmentInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        data = {
            "Physical Security": assessment.physical_security.model_dump(),
            "Access Control": assessment.access_control.model_dump(),
            "Personnel": assessment.personnel.model_dump(),
            "Incident History": assessment.incident_history.model_dump(),
            "Emergency Preparedness": assessment.emergency_preparedness.model_dump(),
        }
        category_scores, contributions, overall_score = compute_scores(data)
        badge, risk_level_name, color = risk_level(overall_score)
        db_assessment = crud.create_assessment(db, assessment, user_id=current_user.id)
        db_assessment = crud.update_assessment_results(
            db, db_assessment.id, category_scores, contributions, overall_score, risk_level_name
        )
        return schemas.RiskAssessmentResponse(
            id=db_assessment.id,
            facility_name=db_assessment.facility_name,
            created_at=db_assessment.created_at,
            category_scores=category_scores,
            contributions=contributions,
            overall_score=overall_score,
            risk_level=risk_level_name,
        )
    except Exception:
        logger.exception("Failed to create risk assessment")
        raise HTTPException(status_code=400, detail="Could not process assessment")


@router.get("/assess/{assessment_id}", response_model=schemas.RiskAssessmentResponse)
def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_assessment = crud.get_assessment(db, assessment_id, user_id=current_user.id)
    if not db_assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return schemas.RiskAssessmentResponse(
        id=db_assessment.id,
        facility_name=db_assessment.facility_name,
        created_at=db_assessment.created_at,
        category_scores=db_assessment.category_scores or {},
        contributions=db_assessment.contributions or {},
        overall_score=db_assessment.overall_score or 0,
        risk_level=db_assessment.risk_level or "Unknown",
    )


@router.get("/assessments")
def list_assessments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    assessments = crud.get_all_assessments(db, user_id=current_user.id, skip=skip, limit=limit)
    return [
        schemas.RiskAssessmentResponse(
            id=a.id,
            facility_name=a.facility_name,
            created_at=a.created_at,
            category_scores=a.category_scores or {},
            contributions=a.contributions or {},
            overall_score=a.overall_score or 0,
            risk_level=a.risk_level or "Unknown",
        )
        for a in assessments
    ]


@router.post("/anomaly/{assessment_id}", response_model=schemas.AnomalyDetectionResponse)
def detect_anomalies(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_assessment = crud.get_assessment(db, assessment_id, user_id=current_user.id)
    if not db_assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    try:
        anomalies = run_anomaly_engine(db_assessment.input_data)
        return schemas.AnomalyDetectionResponse(
            total_anomalies=len(anomalies),
            anomalies=[schemas.AnomalyAlert(**a) for a in anomalies],
            status="success" if len(anomalies) == 0 else "warning",
        )
    except Exception:
        logger.exception("Anomaly detection failed for assessment %s", assessment_id)
        raise HTTPException(status_code=400, detail="Could not run anomaly detection")


@router.post("/predict/{assessment_id}", response_model=schemas.AIPredictionResponse)
def predict_risk(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Run ML model predictions for a completed assessment."""
    db_assessment = crud.get_assessment(db, assessment_id, user_id=current_user.id)
    if not db_assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not db_assessment.category_scores:
        raise HTTPException(status_code=400, detail="Assessment has no computed scores")

    try:
        assessment_data = {
            "overall_score": db_assessment.overall_score or 0.0,
            "category_scores": db_assessment.category_scores,
        }
        predictions = ml_predict(assessment_data)

        # Persist prediction
        crud.create_ai_prediction(
            db,
            assessment_id=assessment_id,
            input_features=assessment_data,
            predictions=predictions,
        )

        return schemas.AIPredictionResponse(
            unauthorized_access=predictions["unauthorized_access"],
            insider_threat=predictions["insider_threat"],
            emergency_failure=predictions["emergency_failure"],
            perimeter_breach=predictions["perimeter_breach"],
        )
    except Exception:
        logger.exception("ML prediction failed for assessment %s", assessment_id)
        raise HTTPException(status_code=500, detail="Prediction failed")
