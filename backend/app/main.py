"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware
import os
from pathlib import Path

from app.config import settings
from app.database import init_db
from app.routers import auth, activities, tiles

# Create FastAPI application
app = FastAPI(
    title="Flashover",
    description="Strava Activity Heatmap Visualization",
    version="0.1.0"
)

# Add session middleware for user authentication
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Register routers
app.include_router(auth.router)
app.include_router(activities.router)
app.include_router(tiles.router)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    # Ensure database directory exists
    db_path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create database tables
    init_db()
    print("✓ Database initialized")
    print(f"✓ Running in {settings.ENVIRONMENT} mode")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


# Mount static files (frontend) - will be available after frontend is built
# In Docker: /app/frontend/dist (because WORKDIR is /app and we COPY backend/ to ./)
# In local dev: /path/to/repo/frontend/dist (backend is in backend/ subdirectory)
if os.environ.get("RUNNING_IN_DOCKER"):
    static_dir = Path("/app/frontend/dist")
else:
    static_dir = Path(__file__).parent.parent.parent / "frontend" / "dist"

if static_dir.exists():
    # Mount the assets directory for CSS/JS files
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        """Serve the frontend application."""
        return FileResponse(str(static_dir / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=settings.is_development)
