"""Activity service for fetching and syncing Strava activities."""
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session

from app.models import User, Activity, SyncLog
from app.services.strava import StravaService
from app.services.polyline import decode_polyline
from app.services.tile_renderer import TileCoordinate


class ActivityService:
    """Service for managing activity data sync with Strava."""

    @staticmethod
    async def sync_user_activities(
        user: User,
        db: Session,
        max_pages: int = 1,
        per_page: int = 200,
        backfill_mode: bool = False
    ) -> Dict:
        """
        Sync activities for a user from Strava API with pagination support.

        Args:
            user: User object with valid tokens
            db: Database session
            max_pages: Maximum number of pages to fetch (default: 1 for quick sync)
            per_page: Activities per page (default: 200, max allowed by Strava)
            backfill_mode: If True, fetch all historical activities (ignore sync log timestamp)

        Returns:
            Dictionary with sync results (new, updated, total counts, has_more, rate_limit)
        """
        # Check if token needs refresh
        if user.is_token_expired:
            await ActivityService._refresh_user_token(user, db)

        # Get last sync time to fetch only new activities (unless in backfill mode)
        sync_log = db.query(SyncLog).filter(SyncLog.user_id == user.id).first()
        after_timestamp = None

        # Only use 'after' timestamp if NOT in backfill mode
        if sync_log and not backfill_mode:
            # Convert last_sync to unix timestamp
            after_timestamp = int(sync_log.last_sync.timestamp())

        new_count = 0
        updated_count = 0
        total_fetched = 0
        has_more = False
        rate_limit_usage = None
        rate_limit_limit = None

        # Fetch activities from Strava with pagination
        for page in range(1, max_pages + 1):
            print(f"Fetching page {page} of activities (per_page={per_page})...")

            activities_data = await StravaService.get_athlete_activities(
                access_token=user.access_token,
                page=page,
                per_page=per_page,
                after=after_timestamp,
            )

            # If no activities returned, we've reached the end
            if not activities_data:
                print(f"No more activities on page {page}, stopping pagination")
                has_more = False
                break

            total_fetched += len(activities_data)

            for activity_data in activities_data:
                strava_id = activity_data["id"]

                # Check if activity already exists
                existing = db.query(Activity).filter(
                    Activity.strava_activity_id == strava_id
                ).first()

                activity_obj = ActivityService._parse_activity_data(activity_data, user.id)

                if existing:
                    # Update existing activity
                    for key, value in activity_obj.items():
                        setattr(existing, key, value)
                    updated_count += 1
                else:
                    # Create new activity
                    new_activity = Activity(**activity_obj)
                    db.add(new_activity)
                    new_count += 1

            # If we got a full page, there might be more
            if len(activities_data) == per_page:
                has_more = True
            else:
                has_more = False
                print(f"Received {len(activities_data)} activities (less than per_page={per_page}), no more pages")
                break

        # Update sync log timestamp only if NOT in backfill mode
        # In backfill mode, we don't update the timestamp so subsequent syncs can continue fetching historical data
        if not backfill_mode:
            if sync_log:
                sync_log.last_sync = datetime.utcnow()
            else:
                sync_log = SyncLog(user_id=user.id, last_sync=datetime.utcnow())
                db.add(sync_log)

        db.commit()

        total_count = db.query(Activity).filter(Activity.user_id == user.id).count()

        print(f"✓ Synced activities: {new_count} new, {updated_count} updated, {total_count} total, {total_fetched} fetched this sync")

        return {
            "new": new_count,
            "updated": updated_count,
            "total": total_count,
            "fetched": total_fetched,
            "has_more": has_more,
            "pages_fetched": page,
            "last_sync": sync_log.last_sync.isoformat() if sync_log else None,
        }

    @staticmethod
    def _calculate_bbox(polyline: str) -> Optional[Tuple[float, float, float, float]]:
        """
        Calculate Web Mercator bounding box for a polyline.

        Args:
            polyline: Encoded polyline string

        Returns:
            Tuple of (min_x, min_y, max_x, max_y) in Web Mercator meters, or None
        """
        if not polyline:
            return None

        try:
            lnglats = decode_polyline(polyline)
            if not lnglats:
                return None

            # Convert all coordinates to Web Mercator
            mercator_coords = []
            for lng, lat in lnglats:
                merc = TileCoordinate.lnglat_to_mercator(lng, lat)
                if merc:
                    mercator_coords.append(merc)

            if not mercator_coords:
                return None

            # Calculate bounding box
            xs = [x for x, y in mercator_coords]
            ys = [y for x, y in mercator_coords]

            return (min(xs), min(ys), max(xs), max(ys))

        except Exception as e:
            print(f"Warning: Error calculating bbox: {e}")
            return None

    @staticmethod
    def _parse_activity_data(activity_data: Dict, user_id: int) -> Dict:
        """
        Parse Strava activity data into our Activity model format.

        Args:
            activity_data: Raw activity data from Strava API
            user_id: User ID to associate with activity

        Returns:
            Dictionary with parsed activity data
        """
        # Parse start date
        start_date = datetime.strptime(
            activity_data["start_date"], "%Y-%m-%dT%H:%M:%SZ"
        )

        # Extract polyline (summary or full)
        polyline = None
        if activity_data.get("map") and activity_data["map"].get("summary_polyline"):
            polyline = activity_data["map"]["summary_polyline"]

        # Calculate bounding box for spatial queries
        bbox = None
        bbox_min_x = None
        bbox_min_y = None
        bbox_max_x = None
        bbox_max_y = None
        if polyline:
            bbox = ActivityService._calculate_bbox(polyline)
            if bbox:
                bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y = bbox

        # Store additional data in extra_data JSON field
        extra_data = {
            "moving_time": activity_data.get("moving_time"),
            "elapsed_time": activity_data.get("elapsed_time"),
            "total_elevation_gain": activity_data.get("total_elevation_gain"),
            "average_speed": activity_data.get("average_speed"),
            "max_speed": activity_data.get("max_speed"),
            "average_heartrate": activity_data.get("average_heartrate"),
            "max_heartrate": activity_data.get("max_heartrate"),
            "start_latlng": activity_data.get("start_latlng"),
            "end_latlng": activity_data.get("end_latlng"),
        }

        return {
            "user_id": user_id,
            "strava_activity_id": activity_data["id"],
            "name": activity_data["name"],
            "type": activity_data["type"],
            "start_date": start_date,
            "distance": activity_data["distance"],
            "polyline": polyline,
            "bbox_min_x": bbox_min_x,
            "bbox_min_y": bbox_min_y,
            "bbox_max_x": bbox_max_x,
            "bbox_max_y": bbox_max_y,
            "extra_data": extra_data,
        }

    @staticmethod
    async def _refresh_user_token(user: User, db: Session) -> None:
        """
        Refresh expired access token for user.

        Args:
            user: User with expired token
            db: Database session
        """
        print(f"Refreshing token for user {user.strava_id}")

        token_data = await StravaService.refresh_token(user.refresh_token)

        # Token refresh doesn't include athlete data, parse manually
        expires_at = datetime.fromtimestamp(token_data["expires_at"])

        user.access_token = token_data["access_token"]
        user.refresh_token = token_data["refresh_token"]
        user.token_expiry = expires_at

        db.commit()
        print(f"✓ Token refreshed for user {user.strava_id}")

    @staticmethod
    def get_activities(
        user: User,
        db: Session,
        activity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Activity]:
        """
        Get activities for a user with optional filters.

        Args:
            user: User to get activities for
            db: Database session
            activity_type: Filter by activity type (Run, Ride, etc.)
            start_date: Filter activities after this date
            end_date: Filter activities before this date

        Returns:
            List of Activity objects
        """
        query = db.query(Activity).filter(Activity.user_id == user.id)

        if activity_type and activity_type != "all":
            query = query.filter(Activity.type == activity_type)

        if start_date:
            query = query.filter(Activity.start_date >= start_date)

        if end_date:
            query = query.filter(Activity.start_date <= end_date)

        return query.order_by(Activity.start_date.desc()).all()
