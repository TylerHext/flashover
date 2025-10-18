/**
 * Polyline decoder for Google's encoded polyline format
 * Used by Strava to encode activity routes
 */

export interface LatLng {
  lat: number;
  lng: number;
}

/**
 * Decode an encoded polyline string into an array of lat/lng coordinates
 *
 * @param encoded - Encoded polyline string from Strava
 * @param precision - Precision factor (default 5 for standard polylines)
 * @returns Array of [lat, lng] coordinate pairs
 */
export function decodePolyline(encoded: string, precision: number = 5): [number, number][] {
  if (!encoded) {
    return [];
  }

  const factor = Math.pow(10, precision);
  const coordinates: [number, number][] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    // Decode latitude
    let shift = 0;
    let result = 0;
    let byte: number;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const deltaLat = (result & 1) ? ~(result >> 1) : (result >> 1);
    lat += deltaLat;

    // Decode longitude
    shift = 0;
    result = 0;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const deltaLng = (result & 1) ? ~(result >> 1) : (result >> 1);
    lng += deltaLng;

    coordinates.push([lat / factor, lng / factor]);
  }

  return coordinates;
}

/**
 * Decode multiple polylines and flatten into single coordinate array
 *
 * @param polylines - Array of encoded polyline strings
 * @returns Flattened array of [lat, lng] coordinate pairs
 */
export function decodeMultiplePolylines(polylines: string[]): [number, number][] {
  const allCoordinates: [number, number][] = [];

  for (const polyline of polylines) {
    if (polyline) {
      const coords = decodePolyline(polyline);
      allCoordinates.push(...coords);
    }
  }

  return allCoordinates;
}
