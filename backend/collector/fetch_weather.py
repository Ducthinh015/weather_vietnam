import os
import json
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any
from pathlib import Path
import requests
from ..config import Config

try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None


DATA_DIR = Path("backend/data/weather")
DATA_DIR.mkdir(parents=True, exist_ok=True)
CITIES_FILE = Path("backend/data/cities.json")
# Retention policy: keep only the latest N records
RETAIN_MIN = 2000


def _ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


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
    item = {
        "timestamp": ts,
        "temp": temp,
        "humidity": humidity,
        "pressure": pressure,
        "wind_speed": wind_speed,
        "rain": rain,
        "cloud": cloud,
    }
    return item


def save_record(record: Dict[str, Any], cfg: Config) -> None:
    if cfg.MONGO_URI and MongoClient is not None:
        client = MongoClient(cfg.MONGO_URI)
        db = client.get_database()
        # insert a copy so that original dict is not mutated with _id
        db.weather.insert_one(dict(record))
        return
    _ensure_dir(cfg.DATA_PATH)
    fp = os.path.join(cfg.DATA_PATH, "weather.json")
    data = []
    if os.path.exists(fp):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
    data.append(record)
    # keep only the latest RETAIN_MIN records
    if len(data) > RETAIN_MIN:
        data = data[-RETAIN_MIN:]
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_record_city(record: Dict[str, Any]) -> None:
    """Save a single city's record to backend/data/weather/<city>.json"""
    city = record.get("city")
    if not city:
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fp = DATA_DIR / f"{city}.json"
    data = []
    if fp.exists():
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
    data.append(record)
    # keep only the latest RETAIN_MIN records per city
    if len(data) > RETAIN_MIN:
        data = data[-RETAIN_MIN:]
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run_once():
    cfg = Config()
    api_key = cfg.WEATHERAPI_KEY or cfg.OPENWEATHER_API_KEY

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

    for city in cities:
        try:
            rec = fetch_current(city, api_key)
            rec["city"] = city
            # Save into legacy dataset (single file) if needed
            save_record(rec, cfg)
            # Save per-city dataset
            save_record_city(rec)
        except Exception:
            # Skip city on error, continue others
            continue


if __name__ == "__main__":
    run_once()
