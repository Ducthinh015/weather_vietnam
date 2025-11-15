from flask import Blueprint, request, jsonify
import logging
import os
import json
import requests
import numpy as np
from datetime import datetime, timezone
from ..ai.gru_model import load_gru
from ..config import Config
from joblib import load as joblib_load
from threading import Thread

weather_bp = Blueprint("weather", __name__)
logger = logging.getLogger(__name__)


@weather_bp.route("/weather/cities", methods=["GET"])
def list_cities():
    """Return list of available cities/provinces.

    Priority:
        1) backend/data/cities.json
        2) CITIES env (comma separated)
    """
    cfg = Config()

    # 1) Try cities.json
    data_dir = os.path.join("backend", "data")
    cities_fp = os.path.join(data_dir, "cities.json")
    cities = []
    if os.path.exists(cities_fp):
        try:
            with open(cities_fp, "r", encoding="utf-8") as f:
                cities = json.load(f)
        except Exception:
            logger.exception("Failed to read cities.json")

    # 2) Fallback: CITIES env
    if not cities:
        raw = getattr(cfg, "CITIES", "") or ""
        if raw:
            cities = [c.strip() for c in raw.split(",") if c.strip()]

    return jsonify(cities)


@weather_bp.route("/weather", methods=["GET"])
def weather_by_city():
    city = (request.args.get("city") or "").strip()
    if not city:
        return jsonify({"error": "missing_city"}), 400

    cfg = Config()
    api_key = cfg.WEATHERAPI_KEY or cfg.OPENWEATHER_API_KEY
    if not api_key:
        return jsonify({"error": "missing_api_key"}), 500

    try:
        res = requests.get(
            "https://api.weatherapi.com/v1/current.json",
            params={"key": api_key, "q": city, "aqi": "no"},
            timeout=20,
        )
        if res.status_code == 400:
            data = res.json()
            return jsonify({"error": data.get("error", {}).get("message", "invalid_city")}), 400
        res.raise_for_status()
        data = res.json()
    except requests.RequestException as exc:
        logger.exception("weather_api_error")
        return jsonify({"error": "weatherapi_unavailable", "detail": str(exc)}), 502

    location = data.get("location", {})
    current = data.get("current", {})
    condition = current.get("condition", {})

    result = {
        "name": location.get("name") or city,
        "coord": {
            "lat": location.get("lat"),
            "lon": location.get("lon"),
        },
        "weather": [
            {
                "description": condition.get("text", ""),
                "icon": condition.get("icon"),
            }
        ],
        "main": {
            "temp": current.get("temp_c"),
            "feels_like": current.get("feelslike_c"),
            "humidity": current.get("humidity"),
            "pressure": current.get("pressure_mb"),
        },
        "wind": {
            "speed": (current.get("wind_kph") or 0.0) / 3.6,
            "deg": current.get("wind_degree"),
        },
        "clouds": {"all": current.get("cloud")},
        "rain": {"1h": current.get("precip_mm")},
        "source": "weatherapi",
        "timestamp": current.get("last_updated"),
    }

    return jsonify(result)

@weather_bp.route("/weather/train-now", methods=["POST"])
def train_now():
    from ..trainer.train_gru import train_all as train_gru

    def _run():
        try:
            train_gru()
        except Exception:
            logger.exception("train_now failed")

    Thread(target=_run, daemon=True).start()
    return jsonify({
        "status": "ok",
        "trained_at": datetime.utcnow().isoformat() + "Z",
    })


@weather_bp.route("/weather/fetch-now", methods=["POST"])
def fetch_now():
    from ..collector.fetch_weather import run_once as fetch_once

    def _run():
        try:
            fetch_once()
        except Exception:
            logger.exception("fetch_now failed")

    Thread(target=_run, daemon=True).start()
    return jsonify({
        "status": "ok",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    })

@weather_bp.route("/weather/realtime", methods=["GET"])
def realtime():
    """Return latest realtime record for a specific city.

    Query params:
        city: required, name of the city/province as in backend/data/cities.json
    """
    city = (request.args.get("city") or "").strip()
    if not city:
        return jsonify({"error": "missing_city"}), 400

    cfg = Config()

    # 1) Try MongoDB first, filtered by city
    if cfg.MONGO_URI:
        try:
            from pymongo import MongoClient

            client = MongoClient(cfg.MONGO_URI)
            db = client.get_database()
            cur = db.weather.find({"city": city}).sort("timestamp", -1).limit(1)
            items = list(cur)
            if items:
                x = items[0]
                x.pop("_id", None)
                return jsonify(x)
        except Exception:
            logger.exception("Mongo realtime failed")

    # 2) Fallback: per-city JSON file backend/data/weather/<city>.json
    data_dir = os.path.join("backend", "data", "weather")
    city_fp = os.path.join(data_dir, f"{city}.json")
    try:
        if os.path.exists(city_fp):
            with open(city_fp, "r", encoding="utf-8") as f:
                arr = json.load(f)
            if arr:
                return jsonify(arr[-1])
    except Exception:
        logger.exception("Per-city realtime file failed")

    # 3) Legacy fallback: single weather.json (no city filter)
    fp = os.path.join(cfg.DATA_PATH, "weather.json")
    try:
        with open(fp, "r", encoding="utf-8") as f:
            arr = json.load(f)
        if arr:
            # best-effort: try to find last record of this city
            for row in reversed(arr):
                if row.get("city") == city:
                    return jsonify(row)
            # otherwise return very last record (legacy behaviour)
            return jsonify(arr[-1])
    except Exception:
        logger.exception("Legacy realtime file failed")

    return jsonify({"error": "no_data_for_city", "city": city}), 404

@weather_bp.route("/weather/predict", methods=["GET"])
def predict_gru():
    """GRU forecast for a specific city.

    Query params:
        city: required, name of the city/province as in backend/data/cities.json
    """
    city = (request.args.get("city") or "").strip()
    if not city:
        return jsonify({"error": "missing_city"}), 400

    cfg = Config()
    # Use the same feature set and sequence lengths as trainer
    features = ["temp", "humidity", "pressure", "wind_speed", "cloud", "rain"]
    seq_in, seq_out = 48, 6

    models_dir = os.path.join("backend", "models")
    model_path = os.path.join(models_dir, f"{city}_gru.h5")
    scaler_path = os.path.join(models_dir, f"{city}_scaler.pkl")
    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        return jsonify({"error": "model_not_trained", "city": city}), 400

    model = load_gru(model_path)
    scaler = joblib_load(scaler_path)

    # 1) Load latest seq_in records for this city from MongoDB if available
    rows = []
    if cfg.MONGO_URI:
        try:
            from pymongo import MongoClient

            client = MongoClient(cfg.MONGO_URI)
            db = client.get_database()
            cur = db.weather.find({"city": city}).sort("timestamp", -1).limit(seq_in)
            rows = list(cur)[::-1]  # chronological
            for r in rows:
                r.pop("_id", None)
        except Exception:
            rows = []

    # 2) Fallback: per-city JSON file backend/data/weather/<city>.json
    if not rows:
        data_dir = os.path.join("backend", "data", "weather")
        city_fp = os.path.join(data_dir, f"{city}.json")
        try:
            if os.path.exists(city_fp):
                with open(city_fp, "r", encoding="utf-8") as f:
                    arr = json.load(f)
                rows = arr[-seq_in:]
        except Exception:
            rows = []

    if len(rows) < seq_in:
        return jsonify({"error": "not_enough_data", "city": city}), 400

    Xdf = [[float(r.get(k, 0.0)) for k in features] for r in rows]
    Xscaled = scaler.transform(np.array(Xdf))
    Xin = np.expand_dims(Xscaled, axis=0)

    y = model.predict(Xin, verbose=0)[0]
    y = y.reshape(seq_out, len(features))
    y_inv = scaler.inverse_transform(y)

    result = {k: [float(v) for v in y_inv[:, i]] for i, k in enumerate(features)}

    return jsonify(
        {
            "city": city,
            "prediction_steps": [f"+{i}h" for i in range(1, seq_out + 1)],
            **result,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
