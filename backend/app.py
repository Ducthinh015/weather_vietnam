import os
from flask import Flask
from .config import Config
from .utils.logger import configure_logging
from flask_cors import CORS


def create_app():
    configure_logging()
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS for API routes
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    from .routes.weather_routes import weather_bp
    from .routes.irrigation_routes import irrigation_bp

    app.register_blueprint(weather_bp, url_prefix="/api")
    app.register_blueprint(irrigation_bp, url_prefix="/api")

    @app.after_request
    def add_no_cache_headers(response):
        # Prevent browsers from caching API responses in dev
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.route("/health")
    def health():
        return {"status": "ok", "name": "AgriCast AI"}

    return app


if __name__ == "__main__":
    # For local development convenience
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
