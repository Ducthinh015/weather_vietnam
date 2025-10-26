import os
from flask import Flask
from .config import Config
from .utils.logger import configure_logging
from flask_cors import CORS
from .db import db
import sys
import logging
from logging.handlers import RotatingFileHandler

"""App factory and DB initialization"""

def create_app():
    configure_logging()
    app = Flask(__name__)
    app.config.from_object(Config)

    if not app.config.get("WEATHERAPI_KEY"):
        print("[AgriCast] WEATHERAPI_KEY is missing in backend/.env. Exiting.")
        sys.exit(1)

    db.init_app(app)

    CORS(app, resources={r"/api/*": {"origins": "*"}, r"/health": {"origins": "*"}})

    from .routes.weather_routes import weather_bp
    from .routes.irrigation_routes import irrigation_bp

    app.register_blueprint(weather_bp, url_prefix="/api")
    app.register_blueprint(irrigation_bp, url_prefix="/api")

    with app.app_context():
        try:
            from .database.models import ForecastHistory 
            db.create_all()
            app.logger.info("Database initialized and tables ensured.")
        except Exception:

            pass

    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    fh = RotatingFileHandler(os.path.join(logs_dir, 'backend.log'), maxBytes=1_000_000, backupCount=3, encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s'))
    app.logger.addHandler(fh)

    @app.after_request
    def add_no_cache_headers(response):

        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.before_request
    def log_request():
        try:
            from flask import request
            app.logger.info(f"REQ {request.method} {request.path} params={dict(request.args)}")
        except Exception:
            pass

    @app.after_request
    def log_response(resp):
        try:
            app.logger.info(f"RESP {resp.status_code} {resp.content_type}")
        except Exception:
            pass
        return resp

    @app.route("/")
    def index():
        return {
            "message": "AgriCast-AI API running",
            "health": "/health",
            "api_examples": [
                "/api/weather?city=Hanoi",
                "/api/forecast?city=Hanoi&hours=5",
                "/api/forecast3?city=Hanoi",
                "/api/history?city=Hanoi&limit=50",
            ],
            "frontend_hint": "Serve frontend/src via a static server, e.g. http://localhost:8080/index.html"
        }

    @app.route("/health")
    def health():
        status = {"status": "ok", "name": "AgriCast AI"}
        key = app.config.get("WEATHERAPI_KEY")
        detail = None
        provider_ok = False
        if not key:
            detail = "WEATHERAPI_KEY missing"
        else:
            try:

                from .services.weather_service import get_current_weather
                get_current_weather("Hanoi", api_key=key)
                provider_ok = True
            except Exception as ex:
                detail = str(ex)
        status.update({"weatherapi": "ok" if provider_ok else "fail", "detail": detail})
        return status

    return app

if __name__ == "__main__":

    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)


