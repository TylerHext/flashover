/**
 * Heatmap rendering with intensity gradient for Strava activities
 */

import L from 'leaflet';
// @ts-ignore - leaflet.heat doesn't have TypeScript definitions
import 'leaflet.heat/dist/leaflet-heat.js';
import { decodeMultiplePolylines } from './polyline';

// Extend Leaflet types for heatmap
declare module 'leaflet' {
  function heatLayer(
    latlngs: [number, number, number?][],
    options?: HeatMapOptions
  ): Layer;

  interface HeatMapOptions {
    minOpacity?: number;
    maxZoom?: number;
    max?: number;
    radius?: number;
    blur?: number;
    gradient?: { [key: number]: string };
  }
}

export interface Activity {
  polyline: string | null;
  type: string;
}

export class HeatmapRenderer {
  private map: L.Map;
  private heatLayer: L.Layer | null = null;

  constructor(map: L.Map) {
    this.map = map;
  }

  /**
   * Render heatmap from activities
   *
   * @param activities - Array of activities with polylines
   * @param options - Heatmap rendering options
   */
  renderHeatmap(activities: Activity[], options?: {
    radius?: number;
    blur?: number;
    maxIntensity?: number;
    gradient?: { [key: number]: string };
  }): void {
    // Clear existing heatmap
    this.clearHeatmap();

    // Extract and decode all polylines
    const polylines = activities
      .filter(a => a.polyline)
      .map(a => a.polyline!);

    if (polylines.length === 0) {
      console.log('No polylines to render');
      return;
    }

    console.log(`Rendering heatmap from ${polylines.length} activities`);

    // Decode all polylines into coordinate array
    const coordinates = decodeMultiplePolylines(polylines);

    console.log(`Decoded ${coordinates.length} coordinate points`);

    if (coordinates.length === 0) {
      console.log('No coordinates decoded');
      return;
    }

    // Create heatmap layer with custom gradient
    // Default: Strava-inspired orange gradient
    const defaultGradient = {
      0.0: '#000080',  // Dark blue (no activity)
      0.2: '#0000ff',  // Blue
      0.4: '#00ff00',  // Green
      0.6: '#ffff00',  // Yellow
      0.8: '#ff8800',  // Orange
      1.0: '#ff0000',  // Red (high activity)
    };

    const heatOptions: L.HeatMapOptions = {
      radius: options?.radius || 15,
      blur: options?.blur || 20,
      maxZoom: 17,
      max: options?.maxIntensity || 1.0,
      gradient: options?.gradient || defaultGradient,
      minOpacity: 0.3,
    };

    // Create and add heatmap layer
    this.heatLayer = L.heatLayer(coordinates, heatOptions);
    this.heatLayer.addTo(this.map);

    console.log('✓ Heatmap rendered successfully');

    // Auto-zoom to fit all activities
    this.fitBounds(coordinates);
  }

  /**
   * Clear the current heatmap layer
   */
  clearHeatmap(): void {
    if (this.heatLayer) {
      this.map.removeLayer(this.heatLayer);
      this.heatLayer = null;
      console.log('Heatmap cleared');
    }
  }

  /**
   * Update heatmap with new options without re-decoding
   *
   * @param _options - New heatmap options (unused - method is informational only)
   */
  updateOptions(_options: {
    radius?: number;
    blur?: number;
    maxIntensity?: number;
  }): void {
    // For leaflet.heat, we need to recreate the layer with new options
    // This is a limitation of the library
    console.log('To update options, call renderHeatmap() again with new options');
  }

  /**
   * Fit map bounds to show all activity coordinates
   *
   * @param coordinates - Array of coordinate pairs
   */
  private fitBounds(coordinates: [number, number][]): void {
    if (coordinates.length === 0) return;

    // Calculate bounds
    const lats = coordinates.map(c => c[0]);
    const lngs = coordinates.map(c => c[1]);

    const southWest: [number, number] = [Math.min(...lats), Math.min(...lngs)];
    const northEast: [number, number] = [Math.max(...lats), Math.max(...lngs)];

    const bounds = L.latLngBounds(southWest, northEast);

    // Fit map to bounds with padding
    this.map.fitBounds(bounds, {
      padding: [50, 50],
      maxZoom: 13,
    });

    console.log('✓ Map auto-zoomed to activity bounds');
  }

  /**
   * Check if heatmap is currently rendered
   */
  isRendered(): boolean {
    return this.heatLayer !== null;
  }
}
