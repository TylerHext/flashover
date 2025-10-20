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
const sidebarHeader = document.getElementById('sidebarHeader');

sidebarHeader?.addEventListener('click', () => {
  sidebar?.classList.toggle('collapsed');
  // Trigger map resize after animation
  setTimeout(() => {
    map.invalidateSize();
  }, 300);
});

// Auth functionality
const loginBtn = document.getElementById('loginBtn');
const logoutBtn = document.getElementById('logoutBtn');
const authStatus = document.getElementById('authStatus');
const syncBtn = document.getElementById('syncBtn');
const loadMoreBtn = document.getElementById('loadMoreBtn');
const resetBtn = document.getElementById('resetBtn');
const syncStatus = document.getElementById('syncStatus');
const syncProgress = document.getElementById('syncProgress');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const statsDiv = document.getElementById('stats');

loginBtn?.addEventListener('click', async () => {
  // Redirect to backend auth endpoint
  window.location.href = '/auth/strava';
});

logoutBtn?.addEventListener('click', async () => {
  try {
    const response = await fetch('/auth/logout', { method: 'POST' });

    if (response.ok) {
      // Clear UI
      if (authStatus) {
        authStatus.innerHTML = '<button id="loginBtn" class="btn btn-primary">Connect to Strava</button>';
        // Re-attach event listener to the new login button
        const newLoginBtn = document.getElementById('loginBtn');
        newLoginBtn?.addEventListener('click', async () => {
          window.location.href = '/auth/strava';
        });
      }

      // Hide all authenticated UI elements
      if (logoutBtn) logoutBtn.style.display = 'none';
      if (syncBtn) syncBtn.style.display = 'none';
      if (loadMoreBtn) loadMoreBtn.style.display = 'none';
      if (resetBtn) resetBtn.style.display = 'none';
      if (syncStatus) syncStatus.innerHTML = '';
      if (syncProgress) syncProgress.style.display = 'none';
      if (statsDiv) statsDiv.innerHTML = '<p>Connect to Strava to see your stats</p>';

      // Clear routes from map
      routeRenderer.clearRoutes();

      console.log('✓ Logged out successfully');
    }
  } catch (error) {
    console.error('Logout failed:', error);
  }
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

      // Show logout, sync and reset buttons
      if (logoutBtn) {
        logoutBtn.style.display = 'block';
      }
      if (syncBtn) {
        syncBtn.style.display = 'block';
      }
      if (resetBtn) {
        resetBtn.style.display = 'block';
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

  (syncBtn as HTMLButtonElement).disabled = true;
  syncBtn.textContent = 'Syncing...';
  syncStatus.innerHTML = '<p class="sync-progress">Fetching recent activities from Strava...</p>';

  // Show progress bar
  if (syncProgress) syncProgress.style.display = 'block';

  try {
    const response = await fetch('/api/activities/sync?pages=1&backfill=true', {
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

    // Show "Load More" button if there are more activities
    if (loadMoreBtn) {
      loadMoreBtn.style.display = data.has_more ? 'block' : 'none';
    }

    // Clear tile cache and reload
    await clearTileCacheAndRender();

  } catch (error) {
    syncStatus.innerHTML = `
      <div class="sync-error">
        <p>✗ Sync failed</p>
        <p class="sync-detail">${error}</p>
      </div>
    `;
    console.error('Sync error:', error);
  } finally {
    (syncBtn as HTMLButtonElement).disabled = false;
    syncBtn.textContent = 'Sync Activities';
  }
});

// Load more activities (deep backfill - 1000 activities per click)
loadMoreBtn?.addEventListener('click', async () => {
  if (!loadMoreBtn || !syncStatus) return;

  (loadMoreBtn as HTMLButtonElement).disabled = true;
  const originalText = loadMoreBtn.textContent;
  loadMoreBtn.textContent = 'Loading...';
  syncStatus.innerHTML = '<p class="sync-progress">Fetching more activities from Strava...</p>';

  try {
    // Fetch 5 pages (1000 activities) in backfill mode
    const response = await fetch('/api/activities/sync?pages=5&backfill=true', {
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

    // Hide button if no more activities
    if (!data.has_more) {
      loadMoreBtn.style.display = 'none';
      syncStatus.innerHTML += '<p class="sync-detail" style="margin-top: 10px;">All historical activities have been loaded.</p>';
    }

    // Clear tile cache and reload
    await clearTileCacheAndRender();

  } catch (error) {
    syncStatus.innerHTML = `
      <div class="sync-error">
        <p>✗ Load more failed</p>
        <p class="sync-detail">${error}</p>
      </div>
    `;
    console.error('Load more error:', error);
  } finally {
    (loadMoreBtn as HTMLButtonElement).disabled = false;
    loadMoreBtn.textContent = originalText || 'Load More Activities';
  }
});

// Reset sync state (DEVELOPMENT ONLY)
resetBtn?.addEventListener('click', async () => {
  if (!resetBtn || !syncStatus) return;

  const confirmed = confirm('⚠️ This will delete ALL activities and reset sync state. Are you sure? This is for testing only.');
  if (!confirmed) return;

  (resetBtn as HTMLButtonElement).disabled = true;
  resetBtn.textContent = 'Resetting...';

  try {
    const response = await fetch('/api/activities/sync/reset', {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Reset failed');
    }

    const data = await response.json();

    syncStatus.innerHTML = `
      <div class="sync-success">
        <p>✓ Reset complete!</p>
        <p class="sync-detail">${data.activities_deleted} activities deleted</p>
        <p class="sync-detail">Sync log cleared - ready for fresh backfill</p>
      </div>
    `;

    console.log('✓ Sync state reset:', data);

    // Hide load more button
    if (loadMoreBtn) {
      loadMoreBtn.style.display = 'none';
    }

    // Reset progress bar
    if (progressFill && progressText) {
      progressFill.style.width = '0%';
      progressText.textContent = '0 activities loaded';
    }

    // Clear routes from map
    routeRenderer.clearRoutes();

    // Reload stats
    loadActivityStats();

  } catch (error) {
    syncStatus.innerHTML = `
      <div class="sync-error">
        <p>✗ Reset failed</p>
        <p class="sync-detail">${error}</p>
      </div>
    `;
    console.error('Reset error:', error);
  } finally {
    (resetBtn as HTMLButtonElement).disabled = false;
    resetBtn.textContent = 'Reset Sync (Dev)';
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

// Helper function to clear tile cache and re-render
async function clearTileCacheAndRender() {
  try {
    // Clear backend tile cache
    console.log('Clearing tile cache...');
    await fetch('/tiles/cache/clear', { method: 'POST' });

    // Reload stats
    loadActivityStats();

    // Re-render routes (this will fetch fresh tiles)
    renderRoutes();

    console.log('✓ Tile cache cleared and routes re-rendered');
  } catch (error) {
    console.error('Failed to clear cache:', error);
    // Still try to render even if cache clear fails
    loadActivityStats();
    renderRoutes();
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
