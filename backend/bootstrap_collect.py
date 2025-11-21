import os
import sys
import time
from pathlib import Path

# Allow running as a script: python backend/bootstrap_collect.py
if __package__ is None or __package__ == "":
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from backend.collector.fetch_weather import run_once  # type: ignore
    from backend.config import Config  # type: ignore
    from backend.db import get_db  # type: ignore
else:
    from .collector.fetch_weather import run_once
    from .config import Config
    from .db import get_db
import json

DEF_SLEEP_SECONDS = 10
TARGET_SAMPLES = 2000  # desired documents per city in Mongo


def _load_cities():
    cfg = Config()
    cities_file = Path("backend/data/cities.json")
    cities = []
    if cities_file.exists():
        try:
            cities = json.loads(cities_file.read_text(encoding="utf-8"))
        except Exception:
            cities = []
    if not cities:
        raw = getattr(cfg, "CITIES", "")
        if raw:
            cities = [c.strip() for c in raw.split(",") if c.strip()]
        if not cities:
            cities = [cfg.CITY]
    return cities


def _mongo_used_rows(city: str) -> int:
    db = get_db()
    return db.weather.count_documents({"province": city})


def main(target: int = TARGET_SAMPLES, sleep_seconds: int = DEF_SLEEP_SECONDS) -> None:
    """Pump real samples into MongoDB until each city reaches target documents.

    Notes:
    - Ensures Mongo weather insert is ENABLED.
    - Each run_once() inserts one new record per city if API succeeds.
    - This can take a long time to reach 2000 docs for all cities.
    """
    # Ensure we insert into Mongo
    os.environ.pop("DISABLE_WEATHER_DB", None)
    cities = _load_cities()
    print(f"[Bootstrap] Start pumping to Mongo for {len(cities)} cities, target={target}")

    while True:
        # Check current min progress in Mongo
        used_counts = {c: _mongo_used_rows(c) for c in cities}
        min_used = min(used_counts.values()) if used_counts else 0
        print("[Bootstrap] Progress:")
        for c, u in used_counts.items():
            print(f"  - {c}: {u}")
        if min_used >= target:
            print("[Bootstrap] All cities reached target docs. Done.")
            break

        # Run one fetch cycle across all cities
        try:
            run_once()
        except Exception as exc:
            print(f"[Bootstrap] fetch run failed: {exc}")
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    # default: target=2000, sleep=10s between runs
    main()
