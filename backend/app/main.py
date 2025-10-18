"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path

from app.config import settings
from app.database import init_db
from app.routers import auth, activities

# Create FastAPI application
app = FastAPI(
    title="Flashover",
    description="Strava Activity Heatmap Visualization",
    version="0.1.0"
)

# Register routers
app.include_router(auth.router)
app.include_router(activities.router)


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
static_dir = os.path.join(os.path.dirname(__file__), "../../frontend/dist")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def serve_frontend():
        """Serve the frontend application."""
        return FileResponse(os.path.join(static_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=settings.is_development)
