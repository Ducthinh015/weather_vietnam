import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS

from backend.config import Config
from backend.db import get_db
from backend.jobs.scheduler import start_scheduler
from backend.utils.responses import ApiError, error_response





def create_app():
    logging.basicConfig(level=logging.INFO)
    app = Flask(__name__)
    app.config.from_object(Config)
    # Allow all origins for local testing/Render frontend
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True, allow_headers=["Content-Type", "Authorization"])

    # Register blueprints using absolute package imports
    from backend.routes.weather_routes import weather_bp
    from backend.routes.irrigation_routes import irrigation_bp
    from backend.routes.auth_routes import auth_bp
    from backend.routes.user_routes import user_bp
    try:
        from backend.routes.cron_routes import cron_bp
    except Exception:
        cron_bp = None

    app.register_blueprint(weather_bp, url_prefix="/api")
    app.register_blueprint(irrigation_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    if cron_bp:
        app.register_blueprint(cron_bp)

    @app.route("/health")
    def health():
        return {"status": "ok", "name": "AgriCast AI"}

    @app.route("/health/db")
    def health_db():
        try:
            db = get_db()
            wc = db.weather.count_documents({})
            mc = db.models.count_documents({})
            hc = db["history_recommendations"].count_documents({})
            return {"weather_count": wc, "model_count": mc, "history_count": hc}
        except Exception as e:
            return {"error": str(e)}, 500

    @app.route("/")
    def index():
        return {"status": "ok"}

    # Register error handlers
    @app.errorhandler(ApiError)
    def handle_api_error(exc: ApiError):
        payload = exc.to_dict()
        return jsonify(payload), exc.status_code

    @app.errorhandler(404)
    def handle_not_found(_: Exception):
        return error_response("not_found", status_code=404, error_code="not_found" )

    @app.errorhandler(Exception)
    def handle_generic_error(exc: Exception):
        logging.exception("Unhandled error")
        return error_response("internal_error", status_code=500, error_code="internal_error")

    # Start background scheduler
    try:
        start_scheduler(app)
    except Exception as ex:
        logging.warning("Scheduler not started: %s", ex)

    return app


# Expose WSGI app for servers like gunicorn: `backend.app:app`
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Disable reloader to prevent WinError 10038 with APScheduler
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
