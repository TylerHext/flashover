"""
Tile-based route rendering with overlap-based gradient coloring.

This module implements a rasterization system that draws route lines onto
tiles and colors them based on overlap intensity.
"""

import math
from typing import List, Tuple, Optional
from io import BytesIO
import numpy as np
from PIL import Image


class LinearGradient:
    """Linear gradient color palette for route overlap visualization."""

    def __init__(self, stops: List[Tuple[int, Tuple[int, int, int, int]]]):
        """
        Initialize a linear gradient with color stops.

        Args:
            stops: List of (threshold, (r, g, b, a)) tuples defining the gradient
        """
        self.palette = np.zeros((256, 4), dtype=np.uint8)

        # Interpolate between stops
        for i in range(len(stops) - 1):
            start_idx, start_color = stops[i]
            end_idx, end_color = stops[i + 1]

            for idx in range(start_idx, end_idx + 1):
                t = (idx - start_idx) / (end_idx - start_idx) if end_idx > start_idx else 0
                self.palette[idx] = self._lerp(start_color, end_color, t)

        # Fill remaining with last color
        if stops:
            last_idx, last_color = stops[-1]
            self.palette[last_idx:] = last_color

    @staticmethod
    def _lerp(
        color_a: Tuple[int, int, int, int],
        color_b: Tuple[int, int, int, int],
        t: float
    ) -> np.ndarray:
        """Linear interpolation between two colors."""
        a = np.array(color_a, dtype=float)
        b = np.array(color_b, dtype=float)
        return ((1 - t) * a + t * b).astype(np.uint8)

    def sample(self, value: int) -> Tuple[int, int, int, int]:
        """Sample the gradient at a given intensity value (0-255)."""
        return tuple(self.palette[min(255, max(0, value))])

    @staticmethod
    def from_hex_colors(min_color: str, mid_color: str, max_color: str, midpoint: int = 10) -> 'LinearGradient':
        """
        Create a gradient from hex color codes.

        Args:
            min_color: Hex color for minimum intensity (e.g., "#ff0000")
            mid_color: Hex color for mid intensity
            max_color: Hex color for maximum intensity
            midpoint: Intensity value (0-255) for mid_color (default: 10)

        Returns:
            LinearGradient instance
        """
        def hex_to_rgba(hex_color: str) -> Tuple[int, int, int, int]:
            """Convert hex color to RGBA tuple."""
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
                return (r, g, b, 255)
            elif len(hex_color) == 8:
                r, g, b, a = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16), int(hex_color[6:8], 16)
                return (r, g, b, a)
            else:
                raise ValueError(f"Invalid hex color: {hex_color}")

        min_rgba = hex_to_rgba(min_color)
        mid_rgba = hex_to_rgba(mid_color)
        max_rgba = hex_to_rgba(max_color)

        # Ensure midpoint is within valid range
        midpoint = max(1, min(254, midpoint))

        return LinearGradient([
            (0, (0, 0, 0, 0)),          # Transparent
            (1, min_rgba),               # Min color
            (midpoint, mid_rgba),        # Mid color
            (255, max_rgba),             # Max color
        ])


# Predefined gradients (matching Rust reference implementation)
ORANGE = LinearGradient([
    (0, (0, 0, 0, 0)),           # Transparent
    (1, (252, 74, 26, 255)),     # Dark orange
    (10, (247, 183, 51, 255)),   # Bright orange
])

PINKISH = LinearGradient([
    (0, (0, 0, 0, 0)),           # Transparent
    (1, (255, 177, 255, 127)),   # Light pink (semi-transparent)
    (10, (255, 177, 255, 255)),  # Pink
    (50, (255, 255, 255, 255)),  # White
])

BLUE_RED = LinearGradient([
    (0, (0, 0, 0, 0)),           # Transparent
    (1, (63, 94, 251, 255)),     # Blue
    (10, (252, 70, 107, 255)),   # Red
    (50, (255, 255, 255, 255)),  # White
])

RED = LinearGradient([
    (0, (0, 0, 0, 0)),           # Transparent
    (1, (178, 10, 44, 255)),     # Dark red
    (10, (255, 251, 213, 255)),  # Light yellow
    (50, (255, 255, 255, 255)),  # White
])


def bresenham_line(x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
    """
    Generate pixel coordinates for a line using Bresenham's algorithm.

    Args:
        x0, y0: Start coordinates
        x1, y1: End coordinates

    Returns:
        List of (x, y) pixel coordinates
    """
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    x, y = x0, y0

    while True:
        points.append((x, y))

        if x == x1 and y == y1:
            break

        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy

    return points


class TileCoordinate:
    """Represents a tile coordinate in the Web Mercator projection."""

    EARTH_RADIUS = 6378137.0
    ORIGIN_SHIFT = 2.0 * math.pi * EARTH_RADIUS / 2.0

    def __init__(self, x: int, y: int, z: int):
        self.x = x
        self.y = y
        self.z = z

    def bounds(self) -> Tuple[float, float, float, float]:
        """
        Get the Web Mercator bounds of this tile.

        Returns:
            (min_x, min_y, max_x, max_y) in Web Mercator meters
        """
        num_tiles = 2 ** self.z
        tile_size = (2.0 * self.ORIGIN_SHIFT) / num_tiles

        min_x = self.x * tile_size - self.ORIGIN_SHIFT
        max_y = self.ORIGIN_SHIFT - self.y * tile_size
        max_x = min_x + tile_size
        min_y = max_y - tile_size

        return (min_x, min_y, max_x, max_y)

    @staticmethod
    def lnglat_to_mercator(lng: float, lat: float) -> Optional[Tuple[float, float]]:
        """
        Convert WGS84 lng/lat to Web Mercator coordinates.

        Args:
            lng: Longitude in degrees
            lat: Latitude in degrees

        Returns:
            (x, y) in Web Mercator meters, or None if out of bounds
        """
        if lat <= -90.0 or lat >= 90.0:
            return None

        x = lng * math.pi / 180.0 * TileCoordinate.EARTH_RADIUS
        y = math.log(math.tan((math.pi * 0.25) + (0.5 * lat * math.pi / 180.0))) * TileCoordinate.EARTH_RADIUS

        return (x, y)


class TileRasterizer:
    """Rasterizes route lines onto a tile with overlap counting."""

    def __init__(self, tile: TileCoordinate, size: int = 512):
        """
        Initialize a tile rasterizer.

        Args:
            tile: The tile coordinate to render
            size: Size of the output tile in pixels (default: 512x512)
        """
        self.tile = tile
        self.size = size
        self.bounds = tile.bounds()
        self.pixels = np.zeros((size, size), dtype=np.uint8)

    def add_polyline(self, lnglats: List[Tuple[float, float]]) -> None:
        """
        Add a polyline to the raster, incrementing pixel counts where it passes.

        Args:
            lnglats: List of (lng, lat) coordinates
        """
        if len(lnglats) < 2:
            return

        # Convert all coordinates to mercator first, keeping track of original indices
        mercator_coords = []
        for i, (lng, lat) in enumerate(lnglats):
            merc = TileCoordinate.lnglat_to_mercator(lng, lat)
            if merc:
                mercator_coords.append((i, merc))  # Store original index with coords

        if len(mercator_coords) < 2:
            return

        # Process line segments with proper clipping
        min_x, min_y, max_x, max_y = self.bounds
        tile_width = max_x - min_x
        tile_height = max_y - min_y

        # Expand tile bounds to include nearby segments
        margin = max(tile_width, tile_height) * 0.2
        expanded_bounds = (
            min_x - margin,
            min_y - margin,
            max_x + margin,
            max_y + margin
        )

        # Process consecutive pairs from the ORIGINAL polyline
        for j in range(len(mercator_coords) - 1):
            idx0, (mx0, my0) = mercator_coords[j]
            idx1, (mx1, my1) = mercator_coords[j + 1]

            # CRITICAL: Only draw if these were consecutive in the original polyline
            # If indices are more than 1 apart, there were points in between that we skipped
            # Drawing would create spurious lines
            if idx1 - idx0 > 1:
                continue

            # Check if either point is near this tile
            point0_near = (expanded_bounds[0] <= mx0 <= expanded_bounds[2] and
                          expanded_bounds[1] <= my0 <= expanded_bounds[3])
            point1_near = (expanded_bounds[0] <= mx1 <= expanded_bounds[2] and
                          expanded_bounds[1] <= my1 <= expanded_bounds[3])

            # Only draw if at least one point is near the tile
            if not (point0_near or point1_near):
                continue

            # Skip obvious GPS jumps
            dist = ((mx1 - mx0) ** 2 + (my1 - my0) ** 2) ** 0.5
            if dist > tile_width * 0.5:
                continue

            # Clip line segment to tile bounds (Cohen-Sutherland algorithm)
            clipped = self._clip_line_to_tile(mx0, my0, mx1, my1)

            if clipped:
                cmx0, cmy0, cmx1, cmy1 = clipped

                # Convert clipped mercator coords to pixels
                px0, py0 = self._mercator_to_pixel_unchecked(cmx0, cmy0)
                px1, py1 = self._mercator_to_pixel_unchecked(cmx1, cmy1)

                # Draw the line segment
                self._draw_line(px0, py0, px1, py1)

    def _clip_line_to_tile(self, x0: float, y0: float, x1: float, y1: float) -> Optional[Tuple[float, float, float, float]]:
        """
        Clip a line segment to tile bounds using Cohen-Sutherland algorithm.

        Returns:
            (x0, y0, x1, y1) clipped coordinates, or None if line is completely outside
        """
        min_x, min_y, max_x, max_y = self.bounds

        # Small epsilon to handle floating-point precision issues
        epsilon = 1e-10

        # Edge codes
        INSIDE = 0  # 0000
        LEFT = 1    # 0001
        RIGHT = 2   # 0010
        BOTTOM = 4  # 0100
        TOP = 8     # 1000

        def compute_edge_code(x: float, y: float) -> int:
            code = INSIDE
            if x < min_x - epsilon:
                code |= LEFT
            elif x > max_x + epsilon:
                code |= RIGHT
            if y < min_y - epsilon:
                code |= BOTTOM
            elif y > max_y + epsilon:
                code |= TOP
            return code

        code0 = compute_edge_code(x0, y0)
        code1 = compute_edge_code(x1, y1)

        while True:
            # Both points inside
            if code0 == INSIDE and code1 == INSIDE:
                # Snap to exact boundary values if very close
                # This ensures consistent pixel mapping across tiles
                if abs(x0 - min_x) < epsilon:
                    x0 = min_x
                if abs(x0 - max_x) < epsilon:
                    x0 = max_x
                if abs(y0 - min_y) < epsilon:
                    y0 = min_y
                if abs(y0 - max_y) < epsilon:
                    y0 = max_y
                if abs(x1 - min_x) < epsilon:
                    x1 = min_x
                if abs(x1 - max_x) < epsilon:
                    x1 = max_x
                if abs(y1 - min_y) < epsilon:
                    y1 = min_y
                if abs(y1 - max_y) < epsilon:
                    y1 = max_y

                return (x0, y0, x1, y1)

            # Both points outside on same side
            if (code0 & code1) != 0:
                return None

            # At least one point outside, clip it
            code_out = code0 if code0 != INSIDE else code1

            # Find intersection point
            # Avoid division by zero
            if code_out & TOP:
                if abs(y1 - y0) > epsilon:
                    x = x0 + (x1 - x0) * (max_y - y0) / (y1 - y0)
                else:
                    x = x0
                y = max_y
            elif code_out & BOTTOM:
                if abs(y1 - y0) > epsilon:
                    x = x0 + (x1 - x0) * (min_y - y0) / (y1 - y0)
                else:
                    x = x0
                y = min_y
            elif code_out & RIGHT:
                if abs(x1 - x0) > epsilon:
                    y = y0 + (y1 - y0) * (max_x - x0) / (x1 - x0)
                else:
                    y = y0
                x = max_x
            elif code_out & LEFT:
                if abs(x1 - x0) > epsilon:
                    y = y0 + (y1 - y0) * (min_x - x0) / (x1 - x0)
                else:
                    y = y0
                x = min_x
            else:
                break

            # Update the point that was outside
            if code_out == code0:
                x0, y0 = x, y
                code0 = compute_edge_code(x0, y0)
            else:
                x1, y1 = x, y
                code1 = compute_edge_code(x1, y1)

        return (x0, y0, x1, y1)

    def _mercator_to_pixel_unchecked(self, mx: float, my: float) -> Tuple[int, int]:
        """
        Convert Web Mercator coordinates to pixel coordinates.
        Assumes coordinates are already within or clipped to tile bounds.

        Args:
            mx, my: Web Mercator coordinates in meters

        Returns:
            (x, y) pixel coordinates
        """
        min_x, min_y, max_x, max_y = self.bounds

        # Convert to pixel coordinates
        width = max_x - min_x
        height = max_y - min_y

        # Use round() instead of int() for consistent rounding across tiles
        # This ensures that the same mercator coordinate maps to the same pixel
        # in adjacent tiles, preventing seams
        px = round((mx - min_x) / width * (self.size - 1))
        py = round((max_y - my) / height * (self.size - 1))  # Flip Y axis

        # Clamp to valid pixel range
        px = max(0, min(self.size - 1, px))
        py = max(0, min(self.size - 1, py))

        return (px, py)

    def _mercator_to_pixel(self, mx: float, my: float) -> Optional[Tuple[int, int]]:
        """
        Convert Web Mercator coordinates to pixel coordinates within the tile.

        Args:
            mx, my: Web Mercator coordinates in meters

        Returns:
            (x, y) pixel coordinates, or None if outside tile bounds
        """
        min_x, min_y, max_x, max_y = self.bounds

        # Check if point is within tile bounds (with small margin)
        margin = (max_x - min_x) * 0.1
        if mx < min_x - margin or mx > max_x + margin:
            return None
        if my < min_y - margin or my > max_y + margin:
            return None

        return self._mercator_to_pixel_unchecked(mx, my)

    def _draw_line(self, x0: int, y0: int, x1: int, y1: int) -> None:
        """
        Draw a line on the raster using Bresenham's algorithm.

        Args:
            x0, y0: Start pixel coordinates
            x1, y1: End pixel coordinates
        """
        # Skip if points are identical
        if x0 == x1 and y0 == y1:
            return

        points = bresenham_line(x0, y0, x1, y1)

        for px, py in points:
            # Bounds check
            if 0 <= px < self.size and 0 <= py < self.size:
                # Saturating add (max at 255)
                if self.pixels[py, px] < 255:
                    self.pixels[py, px] += 1

    def apply_gradient(self, gradient: LinearGradient) -> Image.Image:
        """
        Apply a color gradient to the raster based on pixel counts.

        Args:
            gradient: The gradient to apply

        Returns:
            PIL Image with gradient applied
        """
        # Create RGBA image
        img_array = np.zeros((self.size, self.size, 4), dtype=np.uint8)

        # Apply gradient to each pixel
        for y in range(self.size):
            for x in range(self.size):
                count = self.pixels[y, x]
                img_array[y, x] = gradient.sample(count)

        return Image.fromarray(img_array, mode='RGBA')

    def render_to_png(self, gradient: LinearGradient) -> bytes:
        """
        Render the raster to PNG bytes.

        Args:
            gradient: The gradient to apply

        Returns:
            PNG image as bytes
        """
        img = self.apply_gradient(gradient)
        buffer = BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
