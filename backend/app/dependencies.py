"""Shared FastAPI dependencies"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.config import settings
from app.db import get_db
from app import crud

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def authenticate_token(token: str, db: Session):
    """Validate a JWT string and return the user, or None if invalid.

    Shared by the header-based dependency and the query-param auth used for
    WebSocket / MJPEG endpoints that cannot send Authorization headers.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        email = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
    return crud.get_user_by_email(db, email=email)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Validate JWT and return the current user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user = authenticate_token(token, db)
    if user is None:
        raise credentials_exception
    return user
