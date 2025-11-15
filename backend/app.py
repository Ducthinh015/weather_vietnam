import os
import logging
from flask import Flask
from flask_cors import CORS
from .config import Config
from apscheduler.schedulers.background import BackgroundScheduler


def create_app():
    logging.basicConfig(level=logging.INFO)
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(
        app,
        resources={r"/api/*": {"origins": ["http://localhost:8080", "http://127.0.0.1:8080"]}},
        supports_credentials=False,
        allow_headers=["Content-Type", "Authorization"],
    )

    # Register blueprints
    from .routes.weather_routes import weather_bp
    from .routes.irrigation_routes import irrigation_bp
    from .routes.auth_routes import auth_bp
    from .routes.user_routes import user_bp

    app.register_blueprint(weather_bp, url_prefix="/api")
    app.register_blueprint(irrigation_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(user_bp, url_prefix="/api/user")

    @app.route("/health")
    def health():
        return {"status": "ok", "name": "AgriCast AI"}

    # Scheduler: fetch every FETCH_INTERVAL minutes; train twice daily at 00:00 and 12:00
    if not app.config.get("TESTING", False):
        scheduler = BackgroundScheduler()
        from .collector.fetch_weather import run_once as fetch_once
        from .trainer.train_gru import train_all as train_gru
        cfg = Config()
        scheduler.add_job(fetch_once, "interval", minutes=cfg.FETCH_INTERVAL, id="fetch-weather")
        # Train at 00:00 and 12:00 daily
        scheduler.add_job(train_gru, "cron", hour="0,12", minute="0", id="daily-train")
        scheduler.start()

    return app


if __name__ == "__main__":
    # For local development convenience
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
