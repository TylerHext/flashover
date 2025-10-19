import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { RouteRenderer } from './map/RouteRenderer';

// Initialize the map
const map = L.map('map').setView([33.8761, -118.3965], 12); // Los Angeles area

// Initialize route renderer
const routeRenderer = new RouteRenderer(map);

// Add OpenStreetMap tile layer (dark theme)
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  subdomains: 'abcd',
  maxZoom: 20
}).addTo(map);

// Sidebar collapse functionality
const sidebar = document.getElementById('sidebar');
const collapseBtn = document.getElementById('collapseBtn');

collapseBtn?.addEventListener('click', () => {
  sidebar?.classList.toggle('collapsed');
  // Trigger map resize after animation
  setTimeout(() => {
    map.invalidateSize();
  }, 300);
});

// Auth functionality
const loginBtn = document.getElementById('loginBtn');
const authStatus = document.getElementById('authStatus');
const syncBtn = document.getElementById('syncBtn');
const loadMoreBtn = document.getElementById('loadMoreBtn');
const syncStatus = document.getElementById('syncStatus');
const syncProgress = document.getElementById('syncProgress');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const statsDiv = document.getElementById('stats');

// Track sync state
let hasMoreActivities = false;

loginBtn?.addEventListener('click', async () => {
  // Redirect to backend auth endpoint
  window.location.href = '/auth/strava';
});

// Check authentication status
async function checkAuthStatus() {
  try {
    const response = await fetch('/auth/status');
    const data = await response.json();

    if (data.authenticated) {
      // User is authenticated
      if (authStatus) {
        authStatus.innerHTML = `
          <div class="auth-success">
            <p>✓ Connected to Strava</p>
            <p class="auth-detail">ID: ${data.strava_id}</p>
            ${data.token_expired ? '<p class="auth-warning">Token expired - will refresh on next API call</p>' : ''}
          </div>
        `;
      }

      // Show sync button
      if (syncBtn) {
        syncBtn.style.display = 'block';
      }

      console.log('✓ User authenticated:', data.strava_id);

      // Load activity stats and render routes
      loadActivityStats();
      renderRoutes();
    } else {
      // User not authenticated
      console.log('User not authenticated');
    }
  } catch (error) {
    console.error('Failed to check auth status:', error);
  }
}

// Sync activities from Strava (initial sync - 200 activities)
syncBtn?.addEventListener('click', async () => {
  if (!syncBtn || !syncStatus) return;

  syncBtn.disabled = true;
  syncBtn.textContent = 'Syncing...';
  syncStatus.innerHTML = '<p class="sync-progress">Fetching recent activities from Strava...</p>';

  // Show progress bar
  if (syncProgress) syncProgress.style.display = 'block';

  try {
    const response = await fetch('/api/activities/sync?pages=1', {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Sync failed');
    }

    const data = await response.json();

    // Update progress
    updateSyncProgress(data.total);

    syncStatus.innerHTML = `
      <div class="sync-success">
        <p>✓ Initial sync complete!</p>
        <p class="sync-detail">${data.new} new, ${data.updated} updated</p>
        <p class="sync-detail">Total: ${data.total} activities</p>
        ${data.has_more ? '<p class="sync-detail">More activities available - click "Load More"</p>' : ''}
      </div>
    `;

    console.log('✓ Activities synced:', data);

    // Track if there are more activities
    hasMoreActivities = data.has_more;

    // Show "Load More" button if there are more activities
    if (loadMoreBtn) {
      loadMoreBtn.style.display = data.has_more ? 'block' : 'none';
    }

    // Reload stats and render routes
    loadActivityStats();
    renderRoutes();

  } catch (error) {
    syncStatus.innerHTML = `
      <div class="sync-error">
        <p>✗ Sync failed</p>
        <p class="sync-detail">${error}</p>
      </div>
    `;
    console.error('Sync error:', error);
  } finally {
    syncBtn.disabled = false;
    syncBtn.textContent = 'Sync Activities';
  }
});

// Load more activities (deep backfill - 1000 activities per click)
loadMoreBtn?.addEventListener('click', async () => {
  if (!loadMoreBtn || !syncStatus) return;

  loadMoreBtn.disabled = true;
  const originalText = loadMoreBtn.textContent;
  loadMoreBtn.textContent = 'Loading...';
  syncStatus.innerHTML = '<p class="sync-progress">Fetching more activities from Strava...</p>';

  try {
    // Fetch 5 pages (1000 activities)
    const response = await fetch('/api/activities/sync?pages=5', {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Load more failed');
    }

    const data = await response.json();

    // Update progress
    updateSyncProgress(data.total);

    syncStatus.innerHTML = `
      <div class="sync-success">
        <p>✓ Loaded more activities!</p>
        <p class="sync-detail">${data.fetched} activities fetched</p>
        <p class="sync-detail">Total: ${data.total} activities</p>
        ${data.has_more ? '<p class="sync-detail">More available - click again to continue</p>' : '<p class="sync-detail">All activities loaded!</p>'}
      </div>
    `;

    console.log('✓ More activities loaded:', data);

    // Track if there are more activities
    hasMoreActivities = data.has_more;

    // Hide button if no more activities
    if (!data.has_more) {
      loadMoreBtn.style.display = 'none';
      syncStatus.innerHTML += '<p class="sync-detail" style="margin-top: 10px;">All historical activities have been loaded.</p>';
    }

    // Reload stats and render routes
    loadActivityStats();
    renderRoutes();

  } catch (error) {
    syncStatus.innerHTML = `
      <div class="sync-error">
        <p>✗ Load more failed</p>
        <p class="sync-detail">${error}</p>
      </div>
    `;
    console.error('Load more error:', error);
  } finally {
    loadMoreBtn.disabled = false;
    loadMoreBtn.textContent = originalText || 'Load More Activities';
  }
});

// Update sync progress bar
function updateSyncProgress(total: number) {
  if (!progressText || !progressFill) return;

  progressText.textContent = `${total} activities loaded`;

  // Estimate progress (assume max 3000 activities as typical max)
  const estimatedMax = 3000;
  const percentage = Math.min((total / estimatedMax) * 100, 100);
  progressFill.style.width = `${percentage}%`;
}

// Load activity statistics
async function loadActivityStats() {
  if (!statsDiv) return;

  try {
    const response = await fetch('/api/activities/stats');
    const data = await response.json();

    if (data.total === 0) {
      statsDiv.innerHTML = '<p>No activities yet. Click "Sync Activities" to fetch from Strava.</p>';
      return;
    }

    let statsHtml = `<div class="stat-item"><span class="stat-label">Total</span><span class="stat-value">${data.total}</span></div>`;

    // Add counts by type
    for (const [type, count] of Object.entries(data.by_type)) {
      statsHtml += `<div class="stat-item"><span class="stat-label">${type}</span><span class="stat-value">${count}</span></div>`;
    }

    // Add date range
    if (data.date_range) {
      const earliest = new Date(data.date_range.earliest).toLocaleDateString();
      const latest = new Date(data.date_range.latest).toLocaleDateString();
      statsHtml += `<div class="stat-item"><span class="stat-label">Date Range</span><span class="stat-value">${earliest} - ${latest}</span></div>`;
    }

    statsDiv.innerHTML = statsHtml;

  } catch (error) {
    console.error('Failed to load stats:', error);
    statsDiv.innerHTML = '<p>Failed to load statistics</p>';
  }
}

// Render routes using tile-based visualization
async function renderRoutes() {
  try {
    console.log('Rendering routes...');

    // Check if there are any activities first
    const response = await fetch('/api/activities/stats');
    const data = await response.json();

    if (data.total === 0) {
      console.log('No activities to render');
      return;
    }

    console.log(`Rendering routes for ${data.total} activities`);

    // Render routes with default gradient (orange)
    routeRenderer.renderRoutes({
      gradient: 'orange',
    });

  } catch (error) {
    console.error('Failed to render routes:', error);
  }
}

// Check for auth success in URL
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get('auth') === 'success') {
  console.log('✓ Authentication successful!');
  // Clean up URL
  window.history.replaceState({}, document.title, '/');
  // Check auth status to update UI
  checkAuthStatus();
}

// Gradient tab switching
const presetTab = document.getElementById('presetTab');
const customTab = document.getElementById('customTab');
const presetControls = document.getElementById('presetControls');
const customControls = document.getElementById('customControls');

presetTab?.addEventListener('click', () => {
  presetTab.classList.add('active');
  customTab?.classList.remove('active');
  presetControls?.classList.add('active');
  customControls?.classList.remove('active');
});

customTab?.addEventListener('click', () => {
  customTab.classList.add('active');
  presetTab?.classList.remove('active');
  customControls?.classList.add('active');
  presetControls?.classList.remove('active');
});

// Update midpoint value display
const midpointSlider = document.getElementById('midpoint') as HTMLInputElement;
const midpointValue = document.getElementById('midpointValue');

midpointSlider?.addEventListener('input', () => {
  if (midpointValue) {
    midpointValue.textContent = midpointSlider.value;
  }
});

// Apply gradient
const applyGradientBtn = document.getElementById('applyGradient');
applyGradientBtn?.addEventListener('click', () => {
  const activityType = (document.getElementById('activityType') as HTMLSelectElement)?.value;
  const startDate = (document.getElementById('startDate') as HTMLInputElement)?.value;
  const endDate = (document.getElementById('endDate') as HTMLInputElement)?.value;

  // Check if using custom or preset gradient
  const useCustom = customControls?.classList.contains('active');

  if (useCustom) {
    const minColor = (document.getElementById('minColor') as HTMLInputElement)?.value;
    const midColor = (document.getElementById('midColor') as HTMLInputElement)?.value;
    const maxColor = (document.getElementById('maxColor') as HTMLInputElement)?.value;
    const midpoint = parseInt((document.getElementById('midpoint') as HTMLInputElement)?.value || '10');

    console.log('Applying custom gradient:', { minColor, midColor, maxColor, midpoint });

    routeRenderer.renderRoutes({
      minColor,
      midColor,
      maxColor,
      midpoint,
      activityType: activityType !== 'all' ? activityType : undefined,
      startDate: startDate || undefined,
      endDate: endDate || undefined,
    });
  } else {
    const gradientPreset = (document.getElementById('gradientPreset') as HTMLSelectElement)?.value;

    console.log('Applying preset gradient:', gradientPreset);

    routeRenderer.renderRoutes({
      gradient: gradientPreset,
      activityType: activityType !== 'all' ? activityType : undefined,
      startDate: startDate || undefined,
      endDate: endDate || undefined,
    });
  }
});

// Filter functionality
const applyFiltersBtn = document.getElementById('applyFilters');
applyFiltersBtn?.addEventListener('click', () => {
  // Trigger gradient apply button (which applies both gradient and filters)
  applyGradientBtn?.click();
});

// Health check on load
async function checkHealth() {
  try {
    const response = await fetch('/health');
    const data = await response.json();
    console.log('Backend health check:', data);
  } catch (error) {
    console.error('Backend not available:', error);
  }
}

// Initialize
checkHealth();
checkAuthStatus();

console.log('Flashover frontend initialized');
