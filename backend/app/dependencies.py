"""FastAPI dependencies for authentication and authorization."""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Get the currently authenticated user from the session.

    Raises HTTPException if no user is logged in.
    """
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please log in."
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        # Session has invalid user_id (user was deleted?)
        request.session.clear()
        raise HTTPException(
            status_code=401,
            detail="Session invalid. Please log in again."
        )

    return user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    """
    Get the currently authenticated user from the session, or None if not logged in.

    Use this for endpoints that work differently based on auth status.
    """
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        # Clean up invalid session
        request.session.clear()
        return None

    return user
