"""Strava API service for OAuth and activity data retrieval."""
from datetime import datetime, timedelta
from typing import Dict, Optional
import httpx

from app.config import settings


class StravaService:
    """Service for interacting with Strava API."""

    @staticmethod
    def get_authorization_url(state: Optional[str] = None) -> str:
        """
        Build Strava OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Full authorization URL to redirect user to
        """
        params = {
            "client_id": settings.STRAVA_CLIENT_ID,
            "redirect_uri": settings.STRAVA_REDIRECT_URI,
            "response_type": "code",
            "scope": "activity:read_all",
        }

        if state:
            params["state"] = state

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{settings.STRAVA_AUTH_URL}?{query_string}"

    @staticmethod
    async def exchange_token(code: str) -> Dict:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from Strava callback

        Returns:
            Dictionary containing token data and athlete info

        Raises:
            httpx.HTTPError: If token exchange fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.STRAVA_TOKEN_URL,
                data={
                    "client_id": settings.STRAVA_CLIENT_ID,
                    "client_secret": settings.STRAVA_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def refresh_token(refresh_token: str) -> Dict:
        """
        Refresh an expired access token.

        Args:
            refresh_token: The refresh token from previous authorization

        Returns:
            Dictionary containing new token data

        Raises:
            httpx.HTTPError: If token refresh fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.STRAVA_TOKEN_URL,
                data={
                    "client_id": settings.STRAVA_CLIENT_ID,
                    "client_secret": settings.STRAVA_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    def parse_token_response(token_data: Dict) -> Dict:
        """
        Parse token response from Strava into standardized format.

        Args:
            token_data: Raw token response from Strava

        Returns:
            Dictionary with parsed token info including expiry datetime
        """
        # Strava returns expires_at as unix timestamp
        expires_at = datetime.fromtimestamp(token_data["expires_at"])

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "token_expiry": expires_at,
            "strava_id": token_data["athlete"]["id"],
            "athlete": token_data["athlete"],
        }

    @staticmethod
    async def get_athlete_activities(
        access_token: str,
        page: int = 1,
        per_page: int = 100,
        after: Optional[int] = None,
        before: Optional[int] = None,
    ) -> list:
        """
        Fetch athlete activities from Strava API.

        Args:
            access_token: Valid access token for API requests
            page: Page number for pagination
            per_page: Number of activities per page (max 200)
            after: Unix timestamp to fetch activities after
            before: Unix timestamp to fetch activities before

        Returns:
            List of activity dictionaries

        Raises:
            httpx.HTTPError: If API request fails
        """
        params = {"page": page, "per_page": per_page}

        if after:
            params["after"] = after
        if before:
            params["before"] = before

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.STRAVA_API_BASE}/athlete/activities",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
            response.raise_for_status()
            return response.json()
