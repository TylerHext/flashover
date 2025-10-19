"""Test Web Mercator conversion."""

import sys
sys.path.insert(0, '/Users/tylerhext/repositories/flashover/backend')

from app.services.tile_renderer import TileCoordinate

# Test coordinates from Los Angeles
lng, lat = -118.39483, 33.87554

print(f"Testing Web Mercator conversion for ({lng}, {lat})")

# Convert to mercator
mercator = TileCoordinate.lnglat_to_mercator(lng, lat)
print(f"Web Mercator: {mercator}")

if mercator:
    mx, my = mercator

    # What tile should this be at zoom 12?
    tile_coords = []
    for z in [10, 11, 12, 13, 14]:
        num_tiles = 2 ** z
        scale = num_tiles / (2.0 * 3.14159265359 * 6378137.0 / 2.0)

        tx = int((mx + 20037508.34) * scale)
        ty = int((20037508.34 - my) * scale)

        tile_coords.append((z, tx, ty))
        print(f"  Zoom {z}: tile ({tx}, {ty})")
