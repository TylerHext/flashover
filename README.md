# Flashover

A web application that visualizes your Strava activities with **tile-based route rendering** and **overlap-based gradient coloring**. See your routes as distinct lines that get brighter where they overlap most, revealing your most-traveled paths.

## Features

- **🎨 Overlap-Based Route Coloring**: Routes appear as distinct lines with gradient colors based on frequency
  - Single pass: Dark color
  - Multiple overlaps: Brighter colors
  - Heavy traffic (10+ overlaps): Brightest colors
- **🗺️ Tile-Based Rendering**: Efficient tile system with caching for instant panning/zooming
- **🔐 Strava OAuth Integration**: Secure authentication with your Strava account
- **🎯 Advanced Filters**: Filter by date range and activity type (run, ride, walk, etc.)
- **⚡ Performance Optimized**: In-memory caching and spatial filtering for fast rendering
- **🌙 Dark Theme**: Tech-focused, minimalist UI with dark mode
- **📍 Single-User POC**: Local deployment for personal use

## Tech Stack

- **Backend**: Python 3.11 + FastAPI + NumPy + Pillow
- **Frontend**: TypeScript + Vite + Leaflet.js
- **Database**: SQLite (easily swappable to Postgres)
- **Rendering**: Custom tile rasterizer with Bresenham line drawing + Cohen-Sutherland clipping
- **Deployment**: Docker + Docker Compose

## Project Structure

```
flashover/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI application entry
│   │   ├── config.py               # Configuration & settings
│   │   ├── database.py             # Database setup
│   │   ├── models/                 # Database models (User, Activity, SyncLog)
│   │   ├── routers/
│   │   │   ├── auth.py             # Strava OAuth endpoints
│   │   │   ├── activities.py      # Activity sync and retrieval
│   │   │   └── tiles.py            # Tile rendering endpoints
│   │   └── services/
│   │       ├── strava_service.py   # Strava API client
│   │       ├── activity_service.py # Activity sync logic
│   │       ├── tile_renderer.py    # Core tile rasterization
│   │       └── polyline.py         # Google Polyline decoder
│   ├── requirements.txt            # Python dependencies
│   └── .env.example                # Environment variables template
├── frontend/
│   ├── src/
│   │   ├── index.html              # Main HTML
│   │   ├── main.ts                 # TypeScript entry point
│   │   ├── styles.css              # Application styles
│   │   └── map/
│   │       ├── RouteRenderer.ts    # Leaflet TileLayer wrapper
│   │       └── polyline.ts         # Polyline utilities
│   ├── package.json                # Node dependencies
│   └── vite.config.ts              # Vite configuration with proxies
├── docs/                           # 📚 Technical documentation
│   ├── README.md                   # Documentation index
│   ├── TILE_SEAM_BUG_FIX.md       # Critical bug retrospective
│   ├── PERFORMANCE_OPTIMIZATIONS.md
│   └── ROUTE_VISUALIZATION_UPGRADE.md
├── db/                             # SQLite database (gitignored)
├── Dockerfile                      # Container definition
└── docker-compose.yml              # Docker orchestration
```

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- Strava API credentials (Client ID and Client Secret)
  - Register your app at: https://www.strava.com/settings/api

### Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd flashover
   ```

2. **Configure environment variables**
   ```bash
   cp backend/.env.example backend/.env
   ```

   Edit `backend/.env` and add your Strava credentials:
   ```
   STRAVA_CLIENT_ID=your_client_id_here
   STRAVA_CLIENT_SECRET=your_client_secret_here
   STRAVA_REDIRECT_URI=http://localhost:8080/auth/strava/callback
   ```

3. **Build and run with Docker**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**

   Open your browser to: http://localhost:8080

### Development Mode

For local development with hot-reload:

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Configure your .env
python -m uvicorn app.main:app --reload --port 8080
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev  # Runs on port 3000 with proxy to backend
```

## Usage

1. **Connect to Strava**: Click "Connect to Strava" and grant permissions
2. **Sync Activities**: Click "Sync Activities" to fetch your route data from Strava
3. **Explore Your Routes**:
   - Pan and zoom the map to explore your activities
   - Routes are rendered as tiles (cached for instant viewing)
   - Bright colors show frequently-traveled routes
4. **Apply Filters** (optional):
   - Select activity type (Run, Ride, Walk, etc.)
   - Choose date range
   - Routes update automatically

## How It Works

### Tile-Based Route Rendering

Routes are rendered as **standard web map tiles** (z/x/y format), similar to how Google Maps works:

1. **Rasterization**: Each GPS track is drawn onto a 512×512 pixel grid using Bresenham's line algorithm
2. **Overlap Counting**: Each pixel tracks how many route segments pass through it (0-255)
3. **Gradient Coloring**: Pixel counts map to colors via gradient palette:
   - 1 pass → Dark orange (#fc4a1a)
   - 5 passes → Medium orange
   - 10+ passes → Bright yellow (#f7b733)
4. **Cohen-Sutherland Clipping**: Lines are clipped at exact tile boundaries to prevent seams

### Performance

- **In-memory caching**: Tiles are cached for instant serving on repeat views
- **Spatial filtering**: Only processes activities that intersect each tile
- **Typical performance**: 1-3s first render, < 50ms cached

See [`docs/PERFORMANCE_OPTIMIZATIONS.md`](docs/PERFORMANCE_OPTIMIZATIONS.md) for details.

## Roadmap

### ✅ Completed (MVP)
- [x] Project structure and scaffolding
- [x] Database models (users, activities, sync_log)
- [x] Strava OAuth flow implementation
- [x] Activity data retrieval and sync
- [x] Tile-based route rendering with overlap coloring
- [x] Filter implementation (backend + frontend)
- [x] Performance optimizations (caching, spatial filtering)
- [x] Docker deployment

### 🚀 Future Enhancements
- [ ] Multiple color gradient options in UI
- [ ] Redis caching for production deployments
- [ ] PostgreSQL + PostGIS for spatial indexing
- [ ] Pre-processed tile storage (like Rust reference)
- [ ] Multi-user support
- [ ] Advanced metrics (% roads covered using OSM data)
- [ ] SaaS hosting option

## Documentation

Detailed technical documentation is available in the [`docs/`](docs/) directory:

- **[Route Visualization System](docs/ROUTE_VISUALIZATION_UPGRADE.md)** - Complete system overview
- **[Tile Seam Bug Fix](docs/TILE_SEAM_BUG_FIX.md)** - Critical bug retrospective with solutions
- **[Performance Optimizations](docs/PERFORMANCE_OPTIMIZATIONS.md)** - Caching and optimization strategies

## Architecture Notes

This is designed as a **single-user, local deployment** with architecture that supports future SaaS expansion:

- Database schema includes `user_id` foreign keys (multi-user ready)
- OAuth tokens are stored per user
- Tile rendering is stateless and cacheable
- API endpoints can be extended to support multi-tenancy

## Contributing

This is a personal POC project. Feel free to fork and adapt for your own use!

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Powered by [Strava API](https://developers.strava.com/)
- Map tiles by [CARTO](https://carto.com/)
- Built with [FastAPI](https://fastapi.tiangolo.com/) and [Leaflet](https://leafletjs.com/)
