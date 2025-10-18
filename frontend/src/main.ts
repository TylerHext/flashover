import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { HeatmapRenderer } from './map/heatmap';

// Initialize the map
const map = L.map('map').setView([37.7749, -122.4194], 12); // Default: San Francisco

// Initialize heatmap renderer
const heatmapRenderer = new HeatmapRenderer(map);

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
const syncStatus = document.getElementById('syncStatus');
const statsDiv = document.getElementById('stats');

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

      // Load activity stats and heatmap
      loadActivityStats();
      loadAndRenderHeatmap();
    } else {
      // User not authenticated
      console.log('User not authenticated');
    }
  } catch (error) {
    console.error('Failed to check auth status:', error);
  }
}

// Sync activities from Strava
syncBtn?.addEventListener('click', async () => {
  if (!syncBtn || !syncStatus) return;

  syncBtn.disabled = true;
  syncBtn.textContent = 'Syncing...';
  syncStatus.innerHTML = '<p class="sync-progress">Fetching activities from Strava...</p>';

  try {
    const response = await fetch('/api/activities/sync', {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Sync failed');
    }

    const data = await response.json();

    syncStatus.innerHTML = `
      <div class="sync-success">
        <p>✓ Sync complete!</p>
        <p class="sync-detail">${data.new} new, ${data.updated} updated</p>
        <p class="sync-detail">Total: ${data.total} activities</p>
      </div>
    `;

    console.log('✓ Activities synced:', data);

    // Reload stats and render heatmap
    loadActivityStats();
    loadAndRenderHeatmap();

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

// Load and render heatmap from activities
async function loadAndRenderHeatmap() {
  try {
    console.log('Loading activities for heatmap...');

    const response = await fetch('/api/activities');
    const data = await response.json();

    if (data.count === 0) {
      console.log('No activities to render');
      return;
    }

    console.log(`Loaded ${data.count} activities`);

    // Render heatmap with activities
    heatmapRenderer.renderHeatmap(data.activities, {
      radius: 15,
      blur: 20,
      maxIntensity: 1.0,
    });

  } catch (error) {
    console.error('Failed to load and render heatmap:', error);
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

// Filter functionality
const applyFiltersBtn = document.getElementById('applyFilters');
applyFiltersBtn?.addEventListener('click', () => {
  const activityType = (document.getElementById('activityType') as HTMLSelectElement)?.value;
  const startDate = (document.getElementById('startDate') as HTMLInputElement)?.value;
  const endDate = (document.getElementById('endDate') as HTMLInputElement)?.value;

  console.log('Applying filters:', { activityType, startDate, endDate });
  // TODO: Implement filter logic with backend API
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
