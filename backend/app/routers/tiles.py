"""
Tile rendering endpoints for route visualization.
"""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import Activity
from ..services.tile_renderer import (
    TileCoordinate,
    TileRasterizer,
    LinearGradient,
    ORANGE,
    PINKISH,
    BLUE_RED,
    RED,
)
from ..services.polyline import decode_polyline

router = APIRouter()


# Gradient options
GRADIENTS = {
    "orange": ORANGE,
    "pinkish": PINKISH,
    "blue_red": BLUE_RED,
    "red": RED,
}

# Simple in-memory tile cache
# Note: Clear this when changing rendering logic by restarting server
_tile_cache = {}
_cache_size = 0
MAX_CACHE_SIZE = 100 * 1024 * 1024  # 100MB

# Add cache clear endpoint for development
@router.post("/tiles/cache/clear")
async def clear_cache():
    """Clear the tile cache (useful during development)."""
    global _tile_cache, _cache_size
    _tile_cache.clear()
    _cache_size = 0
    return {"status": "ok", "message": "Cache cleared"}


def _get_cache_key(z: int, x: int, y: int, gradient: str,
                   activity_type: Optional[str], start_date: Optional[str],
                   end_date: Optional[str],
                   min_color: Optional[str], mid_color: Optional[str],
                   max_color: Optional[str], midpoint: Optional[int]) -> str:
    """Generate cache key for tile."""
    filters = f"{activity_type or ''},{start_date or ''},{end_date or ''}"
    custom_gradient = f"{min_color or ''},{mid_color or ''},{max_color or ''},{midpoint or ''}"
    return f"{z},{x},{y},{gradient},{filters},{custom_gradient}"


@router.get("/tiles/{z}/{x}/{y}.png")
async def render_tile(
    z: int,
    x: int,
    y: int,
    db: Session = Depends(get_db),
    gradient: str = Query("orange", description="Color gradient to use"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    min_color: Optional[str] = Query(None, description="Custom gradient: min color (hex)"),
    mid_color: Optional[str] = Query(None, description="Custom gradient: mid color (hex)"),
    max_color: Optional[str] = Query(None, description="Custom gradient: max color (hex)"),
    midpoint: Optional[int] = Query(None, description="Custom gradient: midpoint intensity (1-254)"),
):
    """
    Render a map tile with routes colored by overlap intensity.

    Args:
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate
        gradient: Color gradient name (orange, pinkish, blue_red, red)
        activity_type: Optional activity type filter
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        PNG image tile
    """
    # Validate zoom level
    if z < 0 or z > 18:
        return Response(status_code=400, content="Invalid zoom level")

    # Validate tile coordinates
    max_coord = 2 ** z
    if x < 0 or x >= max_coord or y < 0 or y >= max_coord:
        return Response(status_code=400, content="Invalid tile coordinates")

    # Check cache first
    cache_key = _get_cache_key(z, x, y, gradient, activity_type, start_date, end_date,
                                min_color, mid_color, max_color, midpoint)
    cached = _tile_cache.get(cache_key)
    if cached:
        return Response(
            content=cached,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",
                "X-Cache": "HIT"
            }
        )

    # Get gradient - use custom colors if all three are provided, otherwise use preset
    if min_color and mid_color and max_color:
        try:
            gradient_obj = LinearGradient.from_hex_colors(
                min_color, mid_color, max_color, midpoint or 10
            )
        except ValueError as e:
            return Response(status_code=400, content=f"Invalid hex color: {e}")
    else:
        gradient_obj = GRADIENTS.get(gradient, ORANGE)

    # Create tile coordinate
    tile = TileCoordinate(x, y, z)

    # Get tile bounds for querying activities
    min_x, min_y, max_x, max_y = tile.bounds()

    # Query activities that might intersect with this tile
    # For POC, we'll query all activities and filter client-side
    # In production, you'd want to add spatial indexing
    query = db.query(Activity).filter(Activity.polyline.isnot(None))

    # Apply filters
    if activity_type:
        query = query.filter(Activity.type == activity_type)
    if start_date:
        query = query.filter(Activity.start_date >= start_date)
    if end_date:
        query = query.filter(Activity.start_date <= end_date)

    activities = query.all()

    # If no activities, return transparent tile
    if not activities:
        return Response(
            content=_empty_tile_png(),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"}
        )

    # Create rasterizer
    rasterizer = TileRasterizer(tile, size=512)

    # Spatial filtering: only process activities that intersect tile bounds
    # Expand tile bounds slightly to catch activities that might cross into tile
    tile_bounds_expanded = (
        min_x - (max_x - min_x) * 0.1,
        min_y - (max_y - min_y) * 0.1,
        max_x + (max_x - min_x) * 0.1,
        max_y + (max_y - min_y) * 0.1,
    )

    activities_processed = 0
    activities_skipped = 0

    # Rasterize activities that intersect with tile
    for activity in activities:
        if activity.polyline:
            try:
                # Decode polyline
                lnglats = decode_polyline(activity.polyline)

                # Quick spatial filter: check if any point is near this tile
                # Convert to mercator and check bounds
                intersects = False
                for lng, lat in lnglats:
                    merc = TileCoordinate.lnglat_to_mercator(lng, lat)
                    if merc:
                        mx, my = merc
                        if (tile_bounds_expanded[0] <= mx <= tile_bounds_expanded[2] and
                            tile_bounds_expanded[1] <= my <= tile_bounds_expanded[3]):
                            intersects = True
                            break

                if intersects:
                    # Add to rasterizer
                    rasterizer.add_polyline(lnglats)
                    activities_processed += 1
                else:
                    activities_skipped += 1

            except Exception as e:
                # Skip activities with invalid polylines
                print(f"Error decoding polyline for activity {activity.id}: {e}")
                continue

    # If no activities were rendered, return empty tile
    if activities_processed == 0:
        return Response(
            content=_empty_tile_png(),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"}
        )

    # Render to PNG
    png_bytes = rasterizer.render_to_png(gradient_obj)

    # Cache the tile
    global _cache_size
    if _cache_size + len(png_bytes) > MAX_CACHE_SIZE:
        # Simple eviction: clear entire cache if full
        _tile_cache.clear()
        _cache_size = 0
        print(f"Tile cache cleared")

    _tile_cache[cache_key] = png_bytes
    _cache_size += len(png_bytes)

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Activity-Total": str(len(activities)),
            "X-Activity-Rendered": str(activities_processed),
            "X-Activity-Skipped": str(activities_skipped),
            "X-Cache": "MISS"
        }
    )


def _empty_tile_png() -> bytes:
    """Generate a transparent 512x512 PNG tile."""
    from PIL import Image
    from io import BytesIO

    img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()
