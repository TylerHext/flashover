# Flashover

A web application that visualizes your Strava activities as a personalized, dynamic heatmap. Connect your Strava account, filter by date range or activity type, and see your athletic journey come to life on an interactive map.

## Features (POC)

- **Strava OAuth Integration**: Secure authentication with your Strava account
- **Activity Heatmap**: Visualize all your activities on an interactive map
- **Filters**: Filter by date range and activity type (run, ride, walk, etc.)
- **Dark Theme**: Tech-focused, minimalist UI with dark mode
- **Single-User POC**: Local Docker deployment for personal use

## Tech Stack

- **Backend**: Python 3.11 + FastAPI
- **Frontend**: TypeScript + Leaflet.js
- **Database**: SQLite (easily swappable to Postgres)
- **Deployment**: Docker + Docker Compose

## Project Structure

```
flashover/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application entry
│   │   ├── config.py         # Configuration & settings
│   │   ├── database.py       # Database setup
│   │   ├── models/           # Database models
│   │   ├── routers/          # API endpoints
│   │   └── services/         # Business logic
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Environment variables template
├── frontend/
│   ├── src/
│   │   ├── index.html        # Main HTML
│   │   ├── main.ts           # TypeScript entry point
│   │   ├── styles.css        # Application styles
│   │   └── map/              # Map-related modules
│   ├── package.json          # Node dependencies
│   └── vite.config.ts        # Vite configuration
├── db/                       # SQLite database (gitignored)
├── Dockerfile                # Container definition
└── docker-compose.yml        # Docker orchestration
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

1. Click "Connect to Strava" to authenticate
2. Grant permissions to access your Strava data
3. Your activities will be synced and displayed on the map
4. Use the sidebar filters to customize your view:
   - Select activity type (Run, Ride, Walk, etc.)
   - Choose date range
   - Click "Apply Filters" to update the heatmap

## Roadmap

### MVP
- [x] Project structure and scaffolding
- [x] Database models (users, activities, sync_log)
- [x] Strava OAuth flow implementation
- [x] Activity data retrieval and sync
- [ ] Heatmap rendering with Leaflet
- [ ] Filter implementation (backend + frontend)
- [ ] Docker production deployment

### Future State
- [ ] Multi-user support
- [ ] Advanced metrics (% roads covered using OSM data)
- [ ] SaaS hosting option

## Architecture Notes

This POC is designed as a **single-user, local deployment**. The architecture supports future expansion to multi-user SaaS:

- Database schema includes `user_id` foreign keys
- OAuth tokens are stored per user
- API endpoints can be extended to support multi-tenancy

## Contributing

This is a personal POC project. Feel free to fork and adapt for your own use!

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Powered by [Strava API](https://developers.strava.com/)
- Map tiles by [CARTO](https://carto.com/)
- Built with [FastAPI](https://fastapi.tiangolo.com/) and [Leaflet](https://leafletjs.com/)
