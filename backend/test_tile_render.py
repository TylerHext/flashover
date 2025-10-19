"""Test tile rendering pipeline."""

import sys
sys.path.insert(0, '/Users/tylerhext/repositories/flashover/backend')

from app.services.tile_renderer import TileCoordinate, TileRasterizer, ORANGE
from app.services.polyline import decode_polyline

# Sample polyline from activity 1 (Los Angeles area)
polyline = "ciwmEt~rqU@hAOPgEIO@MNMl@Bd@CRH~@BjCCnBB`CGVUD{AEuA?KBILBpEBl@C`LBLLB`Gs@LBFLR|@v@|BtAfFKJc@N}BjAIJC"

print("Testing full tile rendering pipeline...")

# Decode polyline
coords = decode_polyline(polyline)
print(f"✓ Decoded {len(coords)} coordinates")
print(f"  Lng range: {min(c[0] for c in coords):.6f} to {max(c[0] for c in coords):.6f}")
print(f"  Lat range: {min(c[1] for c in coords):.6f} to {max(c[1] for c in coords):.6f}")

# Create a tile that should contain these coordinates
# Los Angeles is around zoom 12, tiles around (656, 1582)
tile = TileCoordinate(656, 1582, 12)
bounds = tile.bounds()
print(f"\n✓ Created tile z=12, x=656, y=1582")
print(f"  Bounds: {bounds}")

# Check if coordinates are within tile bounds
min_x, min_y, max_x, max_y = bounds
coords_in_tile = sum(1 for lng, lat in coords
                      if min_x <= lng <= max_x and min_y <= lat <= max_y)
print(f"  Coordinates in tile: {coords_in_tile}/{len(coords)}")

# Create rasterizer and render
rasterizer = TileRasterizer(tile, size=512)
print(f"\n✓ Created rasterizer (512x512)")

# Add the polyline
rasterizer.add_polyline(coords)
print(f"✓ Added polyline to raster")

# Check if any pixels were drawn
non_zero = (rasterizer.pixels > 0).sum()
max_value = rasterizer.pixels.max()
print(f"  Non-zero pixels: {non_zero}")
print(f"  Max pixel value: {max_value}")

# Render to PNG
if non_zero > 0:
    png_bytes = rasterizer.render_to_png(ORANGE)
    print(f"\n✓ Rendered to PNG ({len(png_bytes)} bytes)")

    # Save to file for inspection
    with open('test_tile.png', 'wb') as f:
        f.write(png_bytes)
    print("✓ Saved to test_tile.png")
else:
    print("\n✗ No pixels were drawn - check coordinate conversion!")
