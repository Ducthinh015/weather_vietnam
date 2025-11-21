"""Centralized APScheduler configuration."""
from __future__ import annotations

import logging
import os
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from ..collector.fetch_weather import run_once as fetch_once
from ..trainer.train_gru import train_all_sequential as train_job
from ..config import Config

_scheduler: Optional[BackgroundScheduler] = None


def start_scheduler(app) -> Optional[BackgroundScheduler]:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    disable_scheduler = os.getenv("DISABLE_SCHEDULER", "").lower() in ("1", "true", "yes", "on")
    if app.config.get("TESTING", False) or disable_scheduler:
        logging.info("Scheduler disabled (TESTING=%s, DISABLE_SCHEDULER=%s)", app.config.get("TESTING", False), disable_scheduler)
        return None

    cfg = Config()
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_once, "interval", minutes=getattr(cfg, "FETCH_INTERVAL", 10), id="fetch-weather")
    scheduler.add_job(train_job, "cron", hour="*/6", minute="0", id="periodic-train")
    scheduler.start()
    _scheduler = scheduler
    logging.info("Background scheduler started (fetch every %s minutes, train every 6h)", getattr(cfg, "FETCH_INTERVAL", 10))
    return scheduler


def shutdown_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
