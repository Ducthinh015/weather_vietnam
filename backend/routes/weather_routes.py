from flask import Blueprint, request, jsonify, current_app
import logging
import requests
from ..services.weather_service import (
    get_current_weather,
    get_forecast_daily,
    extract_hourly_series,
    get_current_resolved,
)
from ..services.forecast_service import forecast_from_series
from ..models.arima_model import predict_arima_111
from ..database.models import ForecastHistory
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

weather_bp = Blueprint("weather", __name__)
logger = logging.getLogger(__name__)

@weather_bp.route("/weather", methods=["GET"])
def weather():
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "city query param is required"}), 400
    try:

        raw = get_current_resolved(city)

        loc = raw.get("location", {})
        cur = raw.get("current", {})
        out = {
            "name": loc.get("name"),
            "sys": {"country": loc.get("country")},
            "coord": {"lat": loc.get("lat"), "lon": loc.get("lon")},
            "main": {
                "temp": cur.get("temp_c"),
                "feels_like": cur.get("feelslike_c"),
                "humidity": cur.get("humidity"),
                "temp_min": cur.get("temp_c"),
                "temp_max": cur.get("temp_c"),
            },
            "weather": [{"description": (cur.get("condition") or {}).get("text")}],
            "provider": "weatherapi",
        }
        return jsonify(out)
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else 500
        text = e.response.text if e.response is not None else str(e)
        logger.exception("WeatherAPI current error")
        return jsonify({"error": "weatherapi_current_failed", "status": status, "detail": text}), status
    except Exception as e:
        logger.exception("Failed to fetch current weather")
        return jsonify({"error": str(e)}), 500

@weather_bp.route("/forecast", methods=["GET"])
def forecast():
    city = request.args.get("city", "Hanoi")
    hours = int(request.args.get("hours", 5))
    try:
        from ..services.weather_service import get_forecast_data
        data = get_forecast_data(city, hours)
        return jsonify(data)
    except Exception as e:
        logger.exception("Failed to fetch forecast data")
        return jsonify({"error": str(e)}), 500

@weather_bp.route("/forecast3", methods=["GET"])
def forecast3_days():
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "city query param is required"}), 400
    try:
        current = get_current_weather(city, api_key=current_app.config["WEATHERAPI_KEY"])
        fc = get_forecast_daily(city, days=3, api_key=current_app.config["WEATHERAPI_KEY"])
        temps, _ = extract_hourly_series(fc)
        if len(temps) < 12:
            return jsonify({"error": "Not enough data to forecast"}), 400
        preds = predict_arima_111(temps, steps=72)

        day_avgs = []
        for d in range(3):
            chunk = preds[d*24:(d+1)*24]
            avg = round(sum(chunk) / len(chunk), 1) if chunk else None
            day_avgs.append(avg)

        now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
        saved = []
        for i, val in enumerate(day_avgs):
            name = (current.get("location", {}) or {}).get("name") or city
            fh = ForecastHistory(city=name,
                                 timestamp=now + timedelta(days=i+1),
                                 temperature=None,
                                 prediction=val)
            from ..db import db
            db.session.add(fh)
            saved.append(fh)
        from ..db import db
        db.session.commit()

        return jsonify({
            "city": (current.get("location", {}) or {}).get("name"),
            "country": (current.get("location", {}) or {}).get("country"),
            "predictions": [
                {"day": i+1, "avg_temp": v} for i, v in enumerate(day_avgs)
            ]
        })
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else 500
        text = e.response.text if e.response is not None else str(e)
        logger.exception("WeatherAPI forecast3 error")
        return jsonify({"error": "weatherapi_forecast3_failed", "status": status, "detail": text}), status
    except Exception as e:
        logger.exception("Failed to generate 3-day forecast")
        return jsonify({"error": str(e)}), 500

@weather_bp.route("/history", methods=["GET"])
def history():
    city = request.args.get("city")
    limit = int(request.args.get("limit", 50))
    try:
        q = ForecastHistory.query
        if city:
            q = q.filter(ForecastHistory.city.ilike(f"%{city}%"))
        rows = q.order_by(ForecastHistory.timestamp.desc()).limit(limit).all()
        return jsonify([r.to_dict() for r in rows])
    except Exception as e:
        logger.exception("Failed to load history")
        return jsonify({"error": str(e)}), 500

