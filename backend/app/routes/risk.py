"""
Risk assessment routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas, crud
from app.db import get_db
from app.services.risk_service import (
    compute_scores,
    risk_level,
    run_anomaly_engine,
    build_ml_features
)

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.post("/assess", response_model=schemas.RiskAssessmentResponse)
def create_assessment(
    assessment: schemas.RiskAssessmentInput,
    db: Session = Depends(get_db)
):
    """
    Create a new risk assessment and compute scores
    """
    try:
        # Convert Pydantic schema to dict for processing
        data = {
            "Physical Security": assessment.physical_security.model_dump(),
            "Access Control": assessment.access_control.model_dump(),
            "Personnel": assessment.personnel.model_dump(),
            "Incident History": assessment.incident_history.model_dump(),
            "Emergency Preparedness": assessment.emergency_preparedness.model_dump(),
        }
        
        # Compute scores
        category_scores, contributions, overall_score = compute_scores(data)
        badge, risk_level_name, color = risk_level(overall_score)
        
        # Save to database
        db_assessment = crud.create_assessment(db, assessment)
        db_assessment = crud.update_assessment_results(
            db,
            db_assessment.id,
            category_scores,
            contributions,
            overall_score,
            risk_level_name
        )
        
        return schemas.RiskAssessmentResponse(
            id=db_assessment.id,
            facility_name=db_assessment.facility_name,
            created_at=db_assessment.created_at,
            category_scores=category_scores,
            contributions=contributions,
            overall_score=overall_score,
            risk_level=risk_level_name
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assess/{assessment_id}", response_model=schemas.RiskAssessmentResponse)
def get_assessment(assessment_id: int, db: Session = Depends(get_db)):
    """Get a specific assessment"""
    db_assessment = crud.get_assessment(db, assessment_id)
    
    if not db_assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    return schemas.RiskAssessmentResponse(
        id=db_assessment.id,
        facility_name=db_assessment.facility_name,
        created_at=db_assessment.created_at,
        category_scores=db_assessment.category_scores or {},
        contributions=db_assessment.contributions or {},
        overall_score=db_assessment.overall_score or 0,
        risk_level=db_assessment.risk_level or "Unknown"
    )


@router.get("/assessments")
def list_assessments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all assessments"""
    assessments = crud.get_all_assessments(db, skip=skip, limit=limit)
    return [
        schemas.RiskAssessmentResponse(
            id=a.id,
            facility_name=a.facility_name,
            created_at=a.created_at,
            category_scores=a.category_scores or {},
            contributions=a.contributions or {},
            overall_score=a.overall_score or 0,
            risk_level=a.risk_level or "Unknown"
        )
        for a in assessments
    ]


@router.post("/anomaly/{assessment_id}", response_model=schemas.AnomalyDetectionResponse)
def detect_anomalies(assessment_id: int, db: Session = Depends(get_db)):
    """Detect anomalies in an assessment"""
    db_assessment = crud.get_assessment(db, assessment_id)
    
    if not db_assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    try:
        # Get input data
        data = db_assessment.input_data
        
        # Run anomaly detection
        anomalies = run_anomaly_engine(data)
        
        return schemas.AnomalyDetectionResponse(
            total_anomalies=len(anomalies),
            anomalies=[
                schemas.AnomalyAlert(**anomaly)
                for anomaly in anomalies
            ],
            status="success" if len(anomalies) == 0 else "warning"
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
