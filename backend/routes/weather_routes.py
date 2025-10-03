from flask import Blueprint, request, jsonify, current_app
import logging
from ..services.weather_service import get_current_weather, get_hourly_48h
from ..services.forecast_service import forecast_next_hours

weather_bp = Blueprint("weather", __name__)
logger = logging.getLogger(__name__)


@weather_bp.route("/weather", methods=["GET"])
def weather():
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "city query param is required"}), 400
    try:
        data = get_current_weather(city, api_key=current_app.config["OPENWEATHER_API_KEY"])
        return jsonify(data)
    except Exception as e:
        logger.exception("Failed to fetch current weather")
        return jsonify({"error": str(e)}), 500


@weather_bp.route("/forecast", methods=["GET"])
def forecast():
    city = request.args.get("city")
    hours = int(request.args.get("hours", 5))
    if not city:
        return jsonify({"error": "city query param is required"}), 400
    try:
        current = get_current_weather(city, api_key=current_app.config["OPENWEATHER_API_KEY"])
        lat, lon = current["coord"]["lat"], current["coord"]["lon"]
        hourly = get_hourly_48h(lat, lon, api_key=current_app.config["OPENWEATHER_API_KEY"])
        result = forecast_next_hours(hourly, hours=hours)
        return jsonify({
            "city": current.get("name"),
            "country": current.get("sys", {}).get("country"),
            "current": {
                "temp": current.get("main", {}).get("temp"),
                "feels_like": current.get("main", {}).get("feels_like"),
                "humidity": current.get("main", {}).get("humidity"),
                "temp_min": current.get("main", {}).get("temp_min"),
                "temp_max": current.get("main", {}).get("temp_max"),
                "description": current.get("weather", [{}])[0].get("description")
            },
            "forecast": result
        })
    except Exception as e:
        logger.exception("Failed to generate forecast")
        return jsonify({"error": str(e)}), 500
