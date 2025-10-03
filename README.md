# AgriCast AI

Production-ready weather intelligence for agriculture. AgriCast AI provides current weather, short-term forecasts, and irrigation guidance built on a Flask backend and a clean, decoupled frontend.

## Features
- **Current weather** via OpenWeather API
- **5-hour forecast** using ARIMA-based time-series modeling
- **Irrigation guidance** based on humidity threshold heuristics
- **Clean architecture** with Blueprints, services, and utilities
- **.env-driven config** (no hardcoded keys)
- **CI-ready** with pytest and flake8

## Tech Stack
- **Backend**: Python, Flask, pandas, pmdarima, statsmodels
- **Frontend**: HTML, CSS, vanilla JS, Chart.js (CDN)
- **CI**: GitHub Actions (pytest + flake8)

## Monorepo Structure
```
backend/
  app.py                # Flask app factory (create_app), Blueprints
  config.py             # .env loader, runtime config
  models/
    arima_model.py      # ARIMA train/predict wrapper
  routes/
    weather_routes.py   # /api/weather, /api/forecast
    irrigation_routes.py# /api/irrigation/advice
  services/
    weather_service.py  # OpenWeather API client + caching
    forecast_service.py # Data prep + ARIMA inference
  utils/
    cache.py            # Simple in-memory TTL cache (swap to Redis in prod)
    logger.py           # Structured logging
  tests/
    test_weather.py
    test_forecast.py

frontend/
  src/
    index.html
    styles/
      main.css
    js/
      api.js            # Fetch helpers to backend API
      chart.js          # Chart.js helpers
      ui.js             # DOM wiring and events
    pages/
      home.html
      forecast.html
      irrigation.html

.github/workflows/ci.yml
.env.example
```

## Prerequisites
- Python 3.10+

## Setup
1) Clone and create a virtualenv
```
python -m venv .venv
.venv\Scripts\activate  # Windows
```

2) Backend dependencies
```
pip install -r backend/requirements.txt
```

3) Environment variables
Copy `.env.example` to `.env` and fill your values:
```
OPENWEATHER_API_KEY=your_key_here
CACHE_TTL_SECONDS=600
USE_REDIS=false
```

## Run
Start the Flask backend:
```
python -m backend.app
```
Server runs at `http://localhost:5000`. Health check: `GET /health`.

Frontend is static. Open `frontend/src/index.html` directly or serve with any static server.

API endpoints:
- `GET /api/weather?city=Hanoi`
- `GET /api/forecast?city=Hanoi&hours=5`

## Testing
Run unit tests (pytest):
```
pytest -q
```

## Linting
```
flake8 backend
```

## Continuous Integration
GitHub Actions workflow at `.github/workflows/ci.yml` installs backend deps, runs flake8 and pytest on pushes and PRs to `main`/`master`.

## Notes
- Legacy Flask templates and files from the original hackathon demo remain in `templates/` and `static/`. The new app uses the `backend/` API and `frontend/` static files. You may delete the legacy assets if not needed.
- For production: replace in-memory cache with Redis and front the backend with a proper WSGI server and reverse proxy.
