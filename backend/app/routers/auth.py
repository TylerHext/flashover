"""Authentication router for Strava OAuth flow."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.services.strava import StravaService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/strava")
async def strava_login():
    """
    Initiate Strava OAuth flow.

    Redirects user to Strava authorization page.
    """
    auth_url = StravaService.get_authorization_url()
    return RedirectResponse(url=auth_url)


@router.get("/strava/callback")
async def strava_callback(
    code: str = Query(..., description="Authorization code from Strava"),
    scope: str = Query(None, description="Granted scopes"),
    error: str = Query(None, description="Error from Strava"),
    db: Session = Depends(get_db),
):
    """
    Handle Strava OAuth callback.

    Exchanges authorization code for tokens and stores them in database.
    """
    # Check for authorization errors
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"Strava authorization failed: {error}"
        )

    # Check if user denied required scope
    if scope and "activity:read_all" not in scope:
        raise HTTPException(
            status_code=400,
            detail="Required scope 'activity:read_all' was not granted"
        )

    try:
        # Exchange code for tokens
        token_data = await StravaService.exchange_token(code)
        parsed_data = StravaService.parse_token_response(token_data)

        # Check if user already exists
        user = db.query(User).filter(User.strava_id == parsed_data["strava_id"]).first()

        if user:
            # Update existing user's tokens
            user.access_token = parsed_data["access_token"]
            user.refresh_token = parsed_data["refresh_token"]
            user.token_expiry = parsed_data["token_expiry"]
        else:
            # Create new user
            user = User(
                strava_id=parsed_data["strava_id"],
                access_token=parsed_data["access_token"],
                refresh_token=parsed_data["refresh_token"],
                token_expiry=parsed_data["token_expiry"],
            )
            db.add(user)

        db.commit()
        db.refresh(user)

        print(f"✓ User authenticated: Strava ID {user.strava_id}")

        # Redirect back to frontend with success
        # For POC, we'll just redirect to root - in production you'd set a session/cookie
        redirect_url = f"{settings.FRONTEND_URL}/?auth=success"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        db.rollback()
        print(f"✗ OAuth callback error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete authentication: {str(e)}"
        )


@router.get("/status")
async def auth_status(db: Session = Depends(get_db)):
    """
    Check authentication status.

    For POC: Returns the first (and only) user if authenticated.
    In production, this would check session/cookie for specific user.
    """
    user = db.query(User).first()

    if not user:
        return {
            "authenticated": False,
            "message": "No user authenticated"
        }

    return {
        "authenticated": True,
        "strava_id": user.strava_id,
        "token_expired": user.is_token_expired,
    }
