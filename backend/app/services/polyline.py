"""
Google Polyline encoding/decoding utilities.

Strava uses Google's Polyline encoding format to compress GPS coordinates.
"""

from typing import List, Tuple


def decode_polyline(encoded: str) -> List[Tuple[float, float]]:
    """
    Decode a Google Polyline encoded string into a list of (lng, lat) coordinates.

    Args:
        encoded: Polyline encoded string

    Returns:
        List of (longitude, latitude) tuples in (lng, lat) order
    """
    coordinates = []
    index = 0
    lat = 0
    lng = 0

    while index < len(encoded):
        # Decode latitude
        result = 0
        shift = 0
        while index < len(encoded):
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break

        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat

        # Decode longitude
        result = 0
        shift = 0
        while index < len(encoded):
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break

        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng

        # Append as (lng, lat) - polyline encodes lat first, but we return lng first
        coordinates.append((lng / 1e5, lat / 1e5))

    return coordinates


def encode_polyline(coordinates: List[Tuple[float, float]]) -> str:
    """
    Encode a list of (lng, lat) coordinates into a Google Polyline string.

    Args:
        coordinates: List of (longitude, latitude) tuples

    Returns:
        Polyline encoded string
    """
    encoded = []
    prev_lat = 0
    prev_lng = 0

    for lng, lat in coordinates:
        # Convert to integer representation (precision 1e5)
        lat_int = int(round(lat * 1e5))
        lng_int = int(round(lng * 1e5))

        # Calculate deltas
        dlat = lat_int - prev_lat
        dlng = lng_int - prev_lng

        prev_lat = lat_int
        prev_lng = lng_int

        # Encode latitude
        encoded.extend(_encode_value(dlat))
        # Encode longitude
        encoded.extend(_encode_value(dlng))

    return ''.join(encoded)


def _encode_value(value: int) -> List[str]:
    """Encode a single coordinate delta value."""
    # Left shift and invert if negative
    value = ~(value << 1) if value < 0 else (value << 1)

    chunks = []
    while value >= 0x20:
        chunks.append(chr((0x20 | (value & 0x1f)) + 63))
        value >>= 5

    chunks.append(chr(value + 63))
    return chunks
