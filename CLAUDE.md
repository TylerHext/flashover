# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flashover is a web application that visualizes Strava activities as a personalized, dynamic heatmap. It's currently a single-user POC designed for local Docker deployment, but the architecture supports future expansion to multi-user SaaS.

**Tech Stack:**
- Backend: Python 3.11 + FastAPI + SQLAlchemy
- Frontend: TypeScript + Vite + Leaflet.js
- Database: SQLite (easily swappable to Postgres)
- Deployment: Multi-stage Docker build

## Development Commands

### Local Development (Recommended for active development)

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Configure your Strava credentials
python -m uvicorn app.main:app --reload --port 8080
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev  # Runs on port 3000 with proxy to backend on 8080
```

**Frontend Build:**
```bash
cd frontend
npm run build  # Outputs to frontend/dist
```

### Docker Development

**Production mode:**
```bash
docker-compose up --build
```

**Development mode with hot-reload:**
```bash
docker-compose --profile dev up flashover-dev
```

Access the application at http://localhost:8080

### Testing
No test suite is currently implemented. When adding tests, use pytest for backend and consider vitest for frontend.

## Environment Configuration

1. Copy `backend/.env.example` to `backend/.env`
2. Register a Strava app at https://www.strava.com/settings/api
3. Set the following in `backend/.env`:
   - `STRAVA_CLIENT_ID`: Your Strava app's client ID
   - `STRAVA_CLIENT_SECRET`: Your Strava app's client secret
   - `STRAVA_REDIRECT_URI`: Must match your Strava app settings (default: http://localhost:8080/auth/strava/callback)
   - `FRONTEND_URL`: Set to http://localhost:3000 for local dev, http://localhost:8080 for Docker

## Architecture

### Backend Architecture

**Application Entry:** `backend/app/main.py`
- FastAPI app initialization
- Router registration (auth, activities)
- Static file serving for production (serves built frontend from `frontend/dist`)
- Database initialization on startup

**Configuration:** `backend/app/config.py`
- Environment-based settings using `python-dotenv`
- Strava API endpoints and OAuth configuration
- Database URL configuration

**Database:** `backend/app/database.py`
- SQLAlchemy engine and session management
- `get_db()` dependency for FastAPI route injection
- `init_db()` creates all tables on startup

**Data Models:** `backend/app/models/`
- `User`: Stores Strava OAuth tokens (access_token, refresh_token, token_expiry), includes `is_token_expired` property
- `Activity`: Stores activity metadata and encoded polyline. Includes `extra_data` JSON field for additional Strava data
- `SyncLog`: Tracks last sync timestamp per user for incremental syncing

**Key Relationships:**
- User → Activities (one-to-many)
- User → SyncLog (one-to-one)

**Services:** `backend/app/services/`
- `StravaService`: OAuth flow and Strava API client
  - `get_authorization_url()`: Builds OAuth URL
  - `exchange_token()`: Exchanges auth code for tokens
  - `refresh_token()`: Refreshes expired access tokens
  - `get_athlete_activities()`: Fetches activities with pagination
- `ActivityService`: Activity sync and retrieval logic
  - `sync_user_activities()`: Syncs activities from Strava, handles token refresh, tracks new vs updated
  - `get_activities()`: Queries activities with filters (type, date range)

**API Endpoints:** `backend/app/routers/`
- `/auth/strava`: Initiates OAuth flow (redirects to Strava)
- `/auth/strava/callback`: OAuth callback handler (exchanges code, stores tokens)
- `/auth/status`: Returns authentication status (POC: checks for first user)
- `/api/activities/sync` [POST]: Syncs activities from Strava
- `/api/activities` [GET]: Retrieves activities with optional filters (activity_type, start_date, end_date)
- `/api/activities/stats` [GET]: Returns activity counts by type and date range
- `/health`: Health check endpoint

**POC Authentication Pattern:**
- No session management or cookies in POC
- `/auth/status` and activity endpoints return/use the first user in the database
- In production, implement proper session/cookie-based authentication to support multiple users

### Frontend Architecture

**Entry Point:** `frontend/src/main.ts`
- Initializes Leaflet map with dark CARTO tiles
- Handles authentication flow and status checks
- Manages activity sync and heatmap rendering
- Sidebar collapse functionality

**Map Rendering:** `frontend/src/map/`
- `HeatmapRenderer`: Manages heatmap layer creation using Leaflet.heat
- `polyline.ts`: Decodes Strava's encoded polylines to lat/lng coordinates

**Build System:** Vite with TypeScript
- Dev server runs on port 3000 with proxy to backend (:8080) for `/api` and `/auth` routes
- Production build outputs to `frontend/dist` which backend serves as static files

**OAuth Flow:**
1. User clicks "Connect to Strava" → redirects to `/auth/strava`
2. Backend redirects to Strava authorization page
3. User grants permissions
4. Strava redirects to `/auth/strava/callback` with code
5. Backend exchanges code for tokens, stores in DB, redirects to `/?auth=success`
6. Frontend detects `?auth=success`, checks auth status, loads activities

### Multi-Stage Docker Build

**Stage 1 (frontend-builder):**
- Node 20 slim image
- Installs npm dependencies
- Builds frontend → produces `frontend/dist`

**Stage 2 (final image):**
- Python 3.11 slim image
- Installs backend Python dependencies
- Copies backend code
- Copies built frontend from stage 1 to `frontend/dist`
- Backend serves frontend static files in production

### Data Flow

**Activity Sync Flow:**
1. User clicks "Sync Activities"
2. Frontend calls `POST /api/activities/sync`
3. Backend checks token expiry, refreshes if needed
4. Backend calls Strava API to fetch activities (uses `after` timestamp from last sync)
5. Backend upserts activities to database (creates new or updates existing)
6. Backend updates `SyncLog` with current timestamp
7. Frontend reloads stats and re-renders heatmap

**Heatmap Rendering:**
1. Frontend fetches activities via `GET /api/activities` (with optional filters)
2. Activities include encoded polylines from Strava
3. `HeatmapRenderer.renderHeatmap()` decodes polylines to lat/lng points
4. Leaflet.heat plugin renders heatmap layer on map

## Key Implementation Patterns

**Token Management:**
- Tokens stored per user in database
- `User.is_token_expired` property checks if refresh needed
- `ActivityService._refresh_user_token()` handles automatic refresh before API calls

**Incremental Sync:**
- `SyncLog` tracks last sync timestamp
- Subsequent syncs use `after` parameter to fetch only new activities
- Existing activities are updated, new ones created

**Database ID Mapping:**
- Activities use `strava_activity_id` (unique) for Strava's ID
- Activities use `id` for internal database primary key

**Filter Implementation:**
- Activities are indexed by `type` and `start_date` for efficient filtering
- Frontend filter UI exists but is not fully wired (TODO in codebase)

## Future Enhancements

The codebase is structured to support:
- Multi-user support (user_id foreign keys already in place)
- Session/cookie-based authentication
- PostgreSQL migration (SQLAlchemy ORM already used)
- Advanced metrics using OSM data for road coverage
