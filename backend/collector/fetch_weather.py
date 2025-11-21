import os
import json
import time
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any
from pathlib import Path
import requests
from ..config import Config
import logging
from ..db import get_db

CITIES_FILE = Path("backend/data/cities.json")


def fetch_current(city: str, api_key: str) -> Dict[str, Any]:
    # WeatherAPI current conditions
    # Docs: https://www.weatherapi.com/docs/
    r = requests.get(
        "https://api.weatherapi.com/v1/current.json",
        params={"key": api_key, "q": city, "aqi": "no"},
        timeout=20,
    )
    r.raise_for_status()
    d = r.json()
    cur = d.get("current", {})
    # Use Vietnam local time (Asia/Bangkok, UTC+7)
    ts = datetime.now(ZoneInfo("Asia/Bangkok")).isoformat()
    # Map to existing schema used by routes/trainer
    temp = float(cur.get("temp_c")) if cur.get("temp_c") is not None else 0.0
    humidity = float(cur.get("humidity")) if cur.get("humidity") is not None else 0.0
    pressure = float(cur.get("pressure_mb")) if cur.get("pressure_mb") is not None else 0.0
    # WeatherAPI provides wind_kph; convert to m/s to match prior semantics
    wind_kph = cur.get("wind_kph")
    wind_speed = float(wind_kph) / 3.6 if wind_kph is not None else 0.0
    # Precipitation in mm (not strictly per-hour but acceptable proxy)
    rain = float(cur.get("precip_mm")) if cur.get("precip_mm") is not None else 0.0
    cloud = float(cur.get("cloud")) if cur.get("cloud") is not None else 0.0
    feel = float(cur.get("feelslike_c")) if cur.get("feelslike_c") is not None else None
    uv = float(cur.get("uv")) if cur.get("uv") is not None else None
    condition = (cur.get("condition") or {}).get("text")
    item = {
        "timestamp": ts,
        "temp": temp,
        "humidity": humidity,
        "pressure": pressure,
        "wind_speed": wind_speed,
        "rain": rain,
        "cloud": cloud,
        # Extra fields to support Google Sheets appends
        "wind_kph": float(wind_kph) if wind_kph is not None else None,
        "feel": feel,
        "uv": uv,
        "condition": condition,
        "rain_mm": rain,
    }
    return item


def _to_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _capture_dataset_snapshot(db, city: str):
    latest = db.weather.find({"province": city}).sort("timestamp", -1).limit(1)
    earliest = db.weather.find({"province": city}).sort("timestamp", 1).limit(1)
    latest_doc = next(iter(latest), None)
    earliest_doc = next(iter(earliest), None)

    latest_dt = _to_datetime(latest_doc.get("timestamp")) if latest_doc else None
    earliest_dt = _to_datetime(earliest_doc.get("timestamp")) if earliest_doc else None
    coverage_hours = 0.0
    if latest_dt and earliest_dt:
        coverage_hours = max((latest_dt - earliest_dt).total_seconds() / 3600.0, 0.0)

    db.dataset_history.insert_one(
        {
            "city": city,
            "snapshot_at": datetime.now(timezone.utc),
            "samples": db.weather.count_documents({"province": city}),
            "coverage_hours": coverage_hours,
            "latest_timestamp": latest_dt.isoformat() if latest_dt else None,
        }
    )


def run_once():
    cfg = Config()
    api_key = cfg.WEATHERAPI_KEY or cfg.OPENWEATHER_API_KEY
    db = get_db()
    logger = logging.getLogger(__name__)
    disable_db = os.getenv("DISABLE_WEATHER_DB", "").lower() in ("1", "true", "yes", "on")

    # Load list of cities from backend/data/cities.json if available
    cities = []
    if CITIES_FILE.exists():
        try:
            with open(CITIES_FILE, "r", encoding="utf-8") as f:
                cities = json.load(f)
        except Exception:
            cities = []
    if not cities:
        # Fallback: use CITIES env or single CITY
        raw = getattr(cfg, "CITIES", "")
        if raw:
            cities = [c.strip() for c in raw.split(",") if c.strip()]
        if not cities:
            cities = [cfg.CITY]

    inserted = 0
    for city in cities:
        try:
            rec = fetch_current(city, api_key)
            rec["city"] = city
            rec["province"] = city  # explicit province field
            now_local = datetime.now(ZoneInfo("Asia/Bangkok"))
            rec["timestamp"] = now_local.isoformat()
            # Store UTC timestamp as ISO string to ensure JSON serializable
            rec["timestamp_utc"] = now_local.astimezone(timezone.utc).isoformat()
            if not disable_db:
                # Write to MongoDB (can be disabled via env)
                db.weather.insert_one(dict(rec))
                _capture_dataset_snapshot(db, city)
                inserted += 1
                logger.info("fetch_weather inserted: %s", city)
            else:
                logger.info("fetch_weather (DB disabled), city=%s", city)
            # Sheets integration removed for local Mongo-only setup
        except Exception:
            logger.exception("fetch_weather failed: %s", city)
            continue
    logger.info("fetch_weather done: inserted=%d", inserted)


if __name__ == "__main__":
    run_once()
