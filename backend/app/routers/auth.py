"""Authentication router for Strava OAuth flow."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user_optional
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
    request: Request,
    code: str = Query(..., description="Authorization code from Strava"),
    scope: str = Query(None, description="Granted scopes"),
    error: str = Query(None, description="Error from Strava"),
    db: Session = Depends(get_db),
):
    """
    Handle Strava OAuth callback.

    Exchanges authorization code for tokens, stores them in database, and creates session.
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

        # Set session to track logged-in user
        request.session["user_id"] = user.id

        print(f"✓ User authenticated: Strava ID {user.strava_id}, session created")

        # Redirect back to frontend with success
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
async def auth_status(user: User | None = Depends(get_current_user_optional)):
    """
    Check authentication status for the currently logged-in user.

    Returns user info if authenticated, or authentication: false if not.
    """
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


@router.post("/logout")
async def logout(request: Request):
    """
    Log out the current user.

    Clears the session but preserves user data and activities in the database.
    The user can log back in later without needing to re-sync activities.
    """
    user_id = request.session.get("user_id")
    request.session.clear()

    print(f"✓ User logged out: user_id={user_id}")

    return {
        "success": True,
        "message": "Logged out successfully"
    }
