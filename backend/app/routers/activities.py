"""Activities router for syncing and retrieving Strava activities."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Activity
from app.services.activity import ActivityService

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.post("/sync")
async def sync_activities(
    pages: int = Query(1, ge=1, le=50, description="Number of pages to fetch (1-50)"),
    db: Session = Depends(get_db)
):
    """
    Sync activities from Strava for the authenticated user with pagination support.

    Default: Fetches 1 page (200 activities) for quick sync.
    Use pages parameter to fetch more: pages=5 fetches 1000 activities.

    For POC: Uses the first (and only) user in the database.
    In production, this would use session/cookie to identify the user.
    """
    # Get authenticated user (POC: first user)
    user = db.query(User).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="No authenticated user found. Please login first."
        )

    try:
        result = await ActivityService.sync_user_activities(user, db, max_pages=pages)

        message = f"Synced {result['new']} new activities"
        if result['has_more']:
            message += f" ({result['fetched']} fetched, more available)"

        return {
            "success": True,
            "message": message,
            **result,
        }
    except Exception as e:
        print(f"✗ Sync error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync activities: {str(e)}"
        )


@router.get("")
async def get_activities(
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    start_date: Optional[str] = Query(None, description="Filter activities after this date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter activities before this date (ISO format)"),
    db: Session = Depends(get_db),
):
    """
    Get activities for the authenticated user with optional filters.

    For POC: Uses the first (and only) user in the database.
    In production, this would use session/cookie to identify the user.
    """
    # Get authenticated user (POC: first user)
    user = db.query(User).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="No authenticated user found. Please login first."
        )

    # Parse date filters
    start_datetime = None
    end_datetime = None

    try:
        if start_date:
            start_datetime = datetime.fromisoformat(start_date)
        if end_date:
            end_datetime = datetime.fromisoformat(end_date)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format. Use ISO format (YYYY-MM-DD): {str(e)}"
        )

    # Get activities
    activities = ActivityService.get_activities(
        user=user,
        db=db,
        activity_type=activity_type,
        start_date=start_datetime,
        end_date=end_datetime,
    )

    # Transform to JSON-serializable format
    activities_data = [
        {
            "id": activity.id,
            "strava_id": activity.strava_activity_id,
            "name": activity.name,
            "type": activity.type,
            "start_date": activity.start_date.isoformat(),
            "distance": activity.distance,
            "polyline": activity.polyline,
            "extra_data": activity.extra_data,
        }
        for activity in activities
    ]

    return {
        "count": len(activities_data),
        "activities": activities_data,
    }


@router.get("/sync/status")
async def get_sync_status(db: Session = Depends(get_db)):
    """
    Get sync status for the authenticated user.

    Returns information about last sync time and activity counts.
    """
    # Get authenticated user (POC: first user)
    user = db.query(User).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="No authenticated user found. Please login first."
        )

    # Get sync log
    sync_log = db.query(SyncLog).filter(SyncLog.user_id == user.id).first()

    # Get activity count
    total_activities = db.query(Activity).filter(Activity.user_id == user.id).count()

    return {
        "total_activities": total_activities,
        "last_sync": sync_log.last_sync.isoformat() if sync_log else None,
        "has_synced": sync_log is not None,
    }


@router.get("/stats")
async def get_activity_stats(db: Session = Depends(get_db)):
    """
    Get activity statistics for the authenticated user.

    Returns counts by activity type and date range info.
    """
    # Get authenticated user (POC: first user)
    user = db.query(User).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="No authenticated user found. Please login first."
        )

    # Get all activities for user
    activities = db.query(Activity).filter(Activity.user_id == user.id).all()

    if not activities:
        return {
            "total": 0,
            "by_type": {},
            "date_range": None,
        }

    # Count by type
    type_counts = {}
    for activity in activities:
        type_counts[activity.type] = type_counts.get(activity.type, 0) + 1

    # Get date range
    dates = [a.start_date for a in activities]
    earliest = min(dates)
    latest = max(dates)

    return {
        "total": len(activities),
        "by_type": type_counts,
        "date_range": {
            "earliest": earliest.isoformat(),
            "latest": latest.isoformat(),
        },
    }
