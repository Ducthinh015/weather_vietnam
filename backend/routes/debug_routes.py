from flask import Blueprint, jsonify
import inspect
import backend.services.weather_service as ws

debug_bp = Blueprint("debug", __name__)

@debug_bp.get("/debug/weather_service")
def debug_weather_service():
    # đọc toàn bộ code file weather_service.py dưới dạng text
    source = inspect.getsource(ws)
    return jsonify({"code": source})
