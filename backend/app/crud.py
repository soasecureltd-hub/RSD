"""
CRUD operations for database models
"""
from sqlalchemy.orm import Session
from datetime import datetime
from app import models, schemas
from passlib.context import CryptContext

# argon2id only: no 72-byte password limit, OWASP-recommended, and it avoids
# the passlib<->bcrypt 4.x incompatibility that raised "password cannot be
# longer than 72 bytes". verify_and_update lets us bump argon2 cost params
# transparently on future logins.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def get_user_by_email(db: Session, email: str):
    """Fetch a user by email address."""
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate):
    """Hash password and persist new user."""
    hashed = pwd_context.hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed,
        full_name=user.full_name,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str):
    """Return user if credentials are valid, else None.

    Uses verify_and_update so legacy bcrypt hashes are re-hashed to argon2
    on a successful login.
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    valid, new_hash = pwd_context.verify_and_update(password, user.hashed_password)
    if not valid:
        return None
    if new_hash:
        user.hashed_password = new_hash
        db.commit()
    return user


def create_assessment(
    db: Session,
    assessment: schemas.RiskAssessmentInput,
    user_id: int,
) -> models.Assessment:
    """Create a new risk assessment owned by user_id"""

    # Convert input to dict format for storage
    input_data = {
        "facility_name": assessment.facility_name,
        "physical_security": assessment.physical_security.model_dump(),
        "access_control": assessment.access_control.model_dump(),
        "personnel": assessment.personnel.model_dump(),
        "incident_history": assessment.incident_history.model_dump(),
        "emergency_preparedness": assessment.emergency_preparedness.model_dump(),
    }

    db_assessment = models.Assessment(
        user_id=user_id,
        facility_name=assessment.facility_name,
        input_data=input_data
    )
    db.add(db_assessment)
    db.commit()
    db.refresh(db_assessment)
    return db_assessment


def update_assessment_results(
    db: Session,
    assessment_id: int,
    category_scores: dict,
    contributions: dict,
    overall_score: float,
    risk_level: str
) -> models.Assessment:
    """Update assessment with computed results"""
    assessment = db.query(models.Assessment).filter(
        models.Assessment.id == assessment_id
    ).first()
    
    if assessment:
        assessment.category_scores = category_scores
        assessment.contributions = contributions
        assessment.overall_score = overall_score
        assessment.risk_level = risk_level
        assessment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(assessment)
    
    return assessment


def get_assessment(db: Session, assessment_id: int, user_id: int = None) -> models.Assessment:
    """Get assessment by ID, optionally scoped to an owner."""
    query = db.query(models.Assessment).filter(models.Assessment.id == assessment_id)
    if user_id is not None:
        query = query.filter(models.Assessment.user_id == user_id)
    return query.first()


def get_all_assessments(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Get a user's assessments with pagination"""
    return (
        db.query(models.Assessment)
        .filter(models.Assessment.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_camera_health(
    db: Session,
    camera_id: str,
    health_data: dict
) -> models.CameraHealth:
    """Create camera health record"""
    db_health = models.CameraHealth(
        camera_id=camera_id,
        health_score=health_data["health_score"],
        blur_score=health_data["metrics"].get("blur_score"),
        brightness=health_data["metrics"].get("brightness"),
        contrast=health_data["metrics"].get("contrast"),
        noise_level=health_data["metrics"].get("noise_level"),
        fps=health_data["metrics"].get("fps"),
        issues=health_data.get("issues", [])
    )
    db.add(db_health)
    db.commit()
    db.refresh(db_health)
    return db_health


def get_camera_health_history(
    db: Session,
    camera_id: str,
    limit: int = 100
):
    """Get camera health history"""
    return db.query(models.CameraHealth).filter(
        models.CameraHealth.camera_id == camera_id
    ).order_by(models.CameraHealth.created_at.desc()).limit(limit).all()


def create_ai_prediction(
    db: Session,
    assessment_id: int,
    input_features: dict,
    predictions: dict
) -> models.AIPrediction:
    """Create AI prediction record"""
    db_pred = models.AIPrediction(
        assessment_id=assessment_id,
        input_features=input_features,
        unauthorized_access_prob=predictions.get("unauthorized_access"),
        insider_threat_prob=predictions.get("insider_threat"),
        emergency_failure_prob=predictions.get("emergency_failure"),
        perimeter_breach_prob=predictions.get("perimeter_breach"),
        shap_values=predictions.get("shap_values")
    )
    db.add(db_pred)
    db.commit()
    db.refresh(db_pred)
    return db_pred


def get_ai_prediction(db: Session, assessment_id: int) -> models.AIPrediction:
    """Get AI prediction for assessment"""
    return db.query(models.AIPrediction).filter(
        models.AIPrediction.assessment_id == assessment_id
    ).first()
