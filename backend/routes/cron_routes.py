from flask import Blueprint

# Import using absolute paths so this works on Fly.io where app runs from backend/
try:
    from backend.collector.fetch_weather import run_once as fetch_once  # type: ignore
    from backend.trainer.train_gru import train_all_sequential as retrain_model  # type: ignore
except Exception:  # pragma: no cover
    from ..collector.fetch_weather import run_once as fetch_once  # type: ignore
    from ..trainer.train_gru import train_all_sequential as retrain_model  # type: ignore

cron_bp = Blueprint("cron_bp", __name__)

@cron_bp.get("/cron/fetch-weather")
def cron_fetch():
    fetch_once()
    return {"status": "weather_fetched"}

@cron_bp.get("/cron/train-gru")
def cron_train():
    retrain_model()
    return {"status": "gru_trained"}
