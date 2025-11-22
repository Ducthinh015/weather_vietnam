from flask import Blueprint
from backend.collector.fetch_weather import run_once as fetch_once  # type: ignore
from backend.trainer.train_gru import train_all_sequential as retrain_model  # type: ignore

cron_bp = Blueprint("cron_bp", __name__)

@cron_bp.get("/cron/fetch-weather")
def cron_fetch():
    fetch_once()
    return {"status": "weather_fetched"}

@cron_bp.get("/cron/train-gru")
def cron_train():
    retrain_model()
    return {"status": "gru_trained"}
