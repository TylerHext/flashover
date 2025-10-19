/**
 * Route rendering with overlap-based gradient coloring using custom tiles
 */

import L from 'leaflet';

export interface RouteRendererOptions {
  gradient?: string; // Color gradient name (orange, pinkish, blue_red, red)
  activityType?: string;
  startDate?: string;
  endDate?: string;
  // Custom gradient colors (if provided, overrides gradient preset)
  minColor?: string;
  midColor?: string;
  maxColor?: string;
  midpoint?: number;
}

export class RouteRenderer {
  private map: L.Map;
  private tileLayer: L.TileLayer | null = null;

  constructor(map: L.Map) {
    this.map = map;
  }

  /**
   * Render routes as a tile layer with overlap-based gradient coloring
   *
   * @param options - Rendering options including filters and gradient
   */
  renderRoutes(options?: RouteRendererOptions): void {
    // Clear existing layer
    this.clearRoutes();

    console.log('Rendering routes with tile-based visualization', options);

    // Build query parameters
    const params = new URLSearchParams();

    // Custom gradient colors (takes precedence over preset)
    if (options?.minColor && options?.midColor && options?.maxColor) {
      params.set('min_color', options.minColor);
      params.set('mid_color', options.midColor);
      params.set('max_color', options.maxColor);
      if (options?.midpoint !== undefined) {
        params.set('midpoint', options.midpoint.toString());
      }
    } else if (options?.gradient) {
      params.set('gradient', options.gradient);
    }

    if (options?.activityType) {
      params.set('activity_type', options.activityType);
    }
    if (options?.startDate) {
      params.set('start_date', options.startDate);
    }
    if (options?.endDate) {
      params.set('end_date', options.endDate);
    }

    // Create tile layer URL
    const tileUrl = `/tiles/{z}/{x}/{y}.png${params.toString() ? '?' + params.toString() : ''}`;

    // Create tile layer
    this.tileLayer = L.tileLayer(tileUrl, {
      minZoom: 1,
      maxZoom: 18,
      tileSize: 512,
      zoomOffset: -1, // Adjust for 512px tiles vs 256px standard
      opacity: 1.0,
      attribution: 'Route data from Strava',
    });

    // Add to map
    this.tileLayer.addTo(this.map);

    console.log('✓ Route tile layer added to map');

    // Listen for tile load events
    this.tileLayer.on('tileerror', (error) => {
      console.error('Tile load error:', error);
    });

    this.tileLayer.on('tileload', () => {
      console.log('✓ Tile loaded');
    });
  }

  /**
   * Clear the current route layer
   */
  clearRoutes(): void {
    if (this.tileLayer) {
      this.map.removeLayer(this.tileLayer);
      this.tileLayer = null;
      console.log('Route layer cleared');
    }
  }

  /**
   * Update rendering options (re-renders routes)
   *
   * @param options - New rendering options
   */
  updateOptions(options: RouteRendererOptions): void {
    this.renderRoutes(options);
  }

  /**
   * Check if routes are currently rendered
   */
  isRendered(): boolean {
    return this.tileLayer !== null;
  }

  /**
   * Set opacity of the route layer
   *
   * @param opacity - Opacity value (0.0 to 1.0)
   */
  setOpacity(opacity: number): void {
    if (this.tileLayer) {
      this.tileLayer.setOpacity(opacity);
    }
  }

  /**
   * Bring route layer to front
   */
  bringToFront(): void {
    if (this.tileLayer) {
      this.tileLayer.bringToFront();
    }
  }
}
