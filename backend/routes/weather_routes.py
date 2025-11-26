from flask import Blueprint, request, jsonify
import logging
import requests
from datetime import datetime, timezone
from threading import Thread

from backend.config import Config
from backend.db import get_db
from backend.services.weather_service import WeatherService
from backend.schemas.weather_schemas import CityQuerySchema, DatasetHistoryQuerySchema, TrainAllQuerySchema, OptionalCitySchema
from backend.utils.responses import success_response, error_response, ApiError

weather_bp = Blueprint("weather", __name__)
logger = logging.getLogger(__name__)
svc = WeatherService()


def _load_query(schema, source=None):
    from marshmallow import ValidationError

    data = source
    if data is None:
        data = request.args.to_dict() if hasattr(request.args, "to_dict") else dict(request.args)
    
    try:
        return schema.load(data)
    except ValidationError as exc:
        raise ApiError("validation_error", status_code=400, error_code="validation_error", details=exc.messages)


def _city_source():
    return {
        "city": (request.args.get("city") or request.args.get("province") or "").strip()
    }


@weather_bp.route("/weather/cities", methods=["GET"])
def list_cities():
    return success_response({"cities": svc.list_cities()})


@weather_bp.route("/weather", methods=["GET"])
def weather_by_city():
    query = _load_query(CityQuerySchema(), _city_source())
    city = query["city"]

    cfg = Config()
    api_key = cfg.WEATHERAPI_KEY or cfg.OPENWEATHER_API_KEY
    if not api_key:
        return error_response("missing_api_key", status_code=500, error_code="missing_api_key")

    try:
        res = requests.get(
            "https://api.weatherapi.com/v1/current.json",
            params={"key": api_key, "q": city, "aqi": "no"},
            timeout=20,
        )
        if res.status_code == 400:
            data = res.json()
            return error_response(data.get("error", {}).get("message", "invalid_city"), status_code=400, error_code="invalid_city")
        res.raise_for_status()
        data = res.json()
    except requests.RequestException as exc:
        logger.exception("weather_api_error")
        return error_response("weatherapi_unavailable", status_code=502, error_code="upstream_unavailable", details={"detail": str(exc)})

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

    return success_response({"city": city, "weather": result})

@weather_bp.route("/weather/train-now", methods=["POST", "GET"])
def train_now():
    import requests, os

    token = os.getenv("GITHUB_PAT")
    repo  = os.getenv("GITHUB_REPO")

    if not token or not repo:
        return error_response(
            "GitHub settings missing",
            code="github_missing",
            details={"GITHUB_PAT": bool(token), "GITHUB_REPO": bool(repo)}
        )

    # GitHub API for dispatching workflow
    url = f"https://api.github.com/repos/{repo}/dispatches"

    headers = {
        "Accept": "application/vnd.github.everest-preview+json",
        "Authorization": f"token {token}"
    }

    payload = {
        "event_type": "manual_train_trigger",
        "client_payload": {"source": "train-now"}
    }

    r = requests.post(url, json=payload, headers=headers)

    if r.status_code not in (200, 204):
        return error_response(
            "GitHub dispatch failed",
            code="github_dispatch_error",
            details={"status": r.status_code, "body": r.text}
        )

    return success_response(
        {"trigger": "github_train_started"},
        "Train job has been triggered on GitHub Actions"
    )

@weather_bp.route("/weather/fetch-now", methods=["POST", "GET"])
def fetch_now():
    try:
        from backend.collector.fetch_weather import run_once as fetch_once
    except Exception as exc:
        return error_response("fetch_not_available", status_code=500, error_code="fetch_not_available", details={"detail": str(exc)})

    def _run():
        try:
            fetch_once()
        except Exception:
            logger.exception("fetch_now failed")

    Thread(target=_run, daemon=True).start()
    return success_response({"trigger": "fetch_now", "fetched_at": datetime.utcnow().isoformat() + "Z"})

@weather_bp.route("/weather/train-city", methods=["POST", "GET"])
def train_city():
    query = _load_query(CityQuerySchema(), _city_source())
    city = query["city"]

    try:
        from backend.trainer.train_gru import build_and_train
    except Exception as exc:
        return error_response("training_not_supported", status_code=501, error_code="training_not_supported", details={"detail": str(exc)})

    result = {"status": "started", "city": city, "started_at": datetime.utcnow().isoformat() + "Z"}

    def _run():
        try:
            msg = build_and_train(city)
            logger.info("train_city result: %s", msg)
        except Exception:
            logger.exception("train_city failed for %s", city)

    Thread(target=_run, daemon=True).start()
    return success_response(result)

@weather_bp.route("/weather/realtime", methods=["GET"])
def realtime():
    query = _load_query(CityQuerySchema(), _city_source())
    data = svc.get_realtime(query["city"])
    return success_response({"city": query["city"], "realtime": data})

@weather_bp.route("/weather/predict", methods=["GET"])
def predict_gru():
    query = _load_query(CityQuerySchema(), _city_source())
    data = svc.get_forecast(query["city"])
    return success_response(data)


@weather_bp.route("/weather/datasets", methods=["GET"])
def dataset_history():
    query = _load_query(DatasetHistoryQuerySchema())
    rows = svc.get_dataset_history(city=query.get("city"), limit=query["limit"])
    return success_response({"items": rows, "city": query.get("city")})


@weather_bp.route("/weather/history", methods=["GET"])
def history_series():
    # Reuse DatasetHistoryQuerySchema for (city, limit)
    query = _load_query(DatasetHistoryQuerySchema())
    city = query.get("city") or (request.args.get("city") or "").strip()
    if not city:
        raise ApiError("city_required", status_code=400, error_code="city_required")
    limit = int(query.get("limit") or 100)
    items = svc.get_recent_series(city, limit=limit)
    return success_response({"city": city, "items": items, "limit": limit})


@weather_bp.route("/weather/dashboard", methods=["GET"])
def dashboard():
    query = request.args or {}
    city = (query.get("city") or "").strip() or None
    data = svc.get_dashboard(city=city)
    return success_response(data)

@weather_bp.route("/weather/train-all", methods=["POST", "GET"])
def train_all_seq():
    try:
        from backend.trainer.train_gru import train_all_sequential
    except Exception as exc:
        return error_response("training_not_supported", status_code=501, error_code="training_not_supported", details={"detail": str(exc)})

    def _run():
        try:
            train_all_sequential()
        except Exception:
            logger.exception("train_all (sequential) failed")

    Thread(target=_run, daemon=True).start()
    return success_response({"status": "started", "mode": "sequential", "started_at": datetime.utcnow().isoformat() + "Z"})


@weather_bp.route("/weather/train-all-parallel", methods=["POST", "GET"])
def train_all_par():
    try:
        from backend.trainer.train_gru import train_all_parallel
    except Exception as exc:
        return error_response("training_not_supported", status_code=501, error_code="training_not_supported", details={"detail": str(exc)})

    query = _load_query(TrainAllQuerySchema())
    workers = query["workers"]

    def _run():
        try:
            train_all_parallel(max_workers=workers)
        except Exception:
            logger.exception("train_all (parallel) failed")

    Thread(target=_run, daemon=True).start()
    return success_response({"status": "started", "mode": "parallel", "workers": workers, "started_at": datetime.utcnow().isoformat() + "Z"})


@weather_bp.route("/weather/model-info", methods=["GET"])
def model_info():
    city = (request.args.get("city") or request.args.get("province") or "").strip()
    if not city:
        return jsonify({"error": "missing_city"}), 400
    db = get_db()
    doc = db.models.find_one({"province": city}) or db.models.find_one({"model_name": f"{city}_gru.h5"})
    if not doc:
        return success_response({"province": city, "exists": False})
    mb = bytes(doc.get("model_bytes") or b"")
    sb = bytes(doc.get("scaler_bytes") or b"")
    return success_response({
        "province": city,
        "exists": True,
        "model_size": len(mb),
        "scaler_size": len(sb),
        "train_date": doc.get("trained_at") or doc.get("updated_at")
    })

@weather_bp.route("/weather/model-check", methods=["GET"])
def model_check():
    query = _load_query(CityQuerySchema(), _city_source())
    province = query["city"]
    db = get_db()
    doc = db.models.find_one({"province": province}) or db.models.find_one({"model_name": f"{province}_gru.h5"})
    if not doc:
        return success_response({"exists": False, "province": province})
    mb = bytes(doc.get("model_bytes") or b"")
    sb = bytes(doc.get("scaler_bytes") or b"")
    return success_response({
        "exists": True,
        "province": province,
        "model_size": len(mb),
        "scaler_size": len(sb),
        "train_date": doc.get("trained_at") or doc.get("updated_at")
    })
