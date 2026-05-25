"""Authentication routes: register, login, me"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from sqlalchemy.orm import Session
from app import schemas, crud
from app.config import settings
from app.db import get_db
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _create_access_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": email, "exp": expire},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


@router.post("/register", response_model=schemas.UserResponse, status_code=201)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db, user)


@router.post("/login", response_model=schemas.Token)
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 form-based login (username field = email). Used by FastAPI's OAuth2 docs."""
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return schemas.Token(access_token=_create_access_token(user.email))


@router.post("/login/json", response_model=schemas.Token)
def login_json(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """JSON body login — convenience endpoint for frontend."""
    user = crud.authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return schemas.Token(access_token=_create_access_token(user.email))


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user=Depends(get_current_user)):
    return current_user
