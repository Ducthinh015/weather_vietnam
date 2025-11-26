from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
from io import BytesIO

import joblib
import numpy as np
from tensorflow import keras
from keras.layers import GRU, Bidirectional
from pymongo.collection import Collection

from backend.config import Config
from backend.db import get_db
from backend.utils.responses import ApiError


# ============================
#  MODEL CONFIG
# ============================
FEATURES = ["temp", "humidity", "pressure", "wind_speed", "cloud", "rain"]
SEQ_IN = 48
SEQ_OUT = 6


@dataclass
class ModelArtifacts:
    scaler: Any
    model: Any     # keras model


class WeatherService:
    def __init__(self):
        self.cfg = Config()
        self.db = get_db()
        self._pkg_root = Path(__file__).resolve().parents[1]
        self.model_base = self._pkg_root / "models" / "weather"
        self._data_dir = self._pkg_root / "data"

    # ==============================================================
    # Cities helper
    # ==============================================================
    def list_cities(self) -> List[str]:
        cities_fp = self._data_dir / "cities.json"
        if cities_fp.exists():
            try:
                payload = json.loads(cities_fp.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    items = payload.get("cities", [])
                else:
                    items = payload
                items = [c for c in items if isinstance(c, str) and c.strip()]
                if items:
                    return items
            except Exception:
                pass

        raw = getattr(self.cfg, "CITIES", "") or ""
        if raw:
            return [c.strip() for c in raw.split(",") if c.strip()]

        return [self.cfg.CITY]

    # ==============================================================
    # Dataset history
    # ==============================================================
    def get_dataset_history(self, city: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        coll: Collection = self.db.dataset_history
        query: Dict[str, Any] = {}
        if city:
            query["city"] = city
        cursor = coll.find(query).sort("snapshot_at", -1).limit(limit)

        out = []
        for doc in cursor:
            doc["id"] = str(doc.pop("_id", ""))
            out.append(doc)
        return out

    # ==============================================================
    # Time series loader
    # ==============================================================
    def get_recent_series(self, city: str, limit: int = 48) -> List[Dict[str, Any]]:
        cursor = (
            self.db.weather
            .find({"province": city}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
        return list(cursor)[::-1]  # đảo lại đúng thứ tự thời gian

    # ==============================================================
    # LOAD MODEL (FS → Mongo) + PATCH GRU & BIDIRECTIONAL
    # ==============================================================
    def _load_model_artifacts(self, city: str) -> ModelArtifacts:

        # ===== PATCH 1: GRU - remove time_major =====
        def patched_gru(**kwargs):
            kwargs.pop("time_major", None)
            return GRU(**kwargs)

        # ===== PATCH 2: Bidirectional - remove time_major inside layer config =====
        def patched_bidirectional(**kwargs):
            layer_cfg = kwargs.get("layer")
            if isinstance(layer_cfg, dict):
                layer_cfg.pop("time_major", None)
            return Bidirectional(keras.layers.deserialize(layer_cfg))

        # ===== PATCH 3: Recursive patch for configs =====
        def recursive_clean(config):
            if isinstance(config, dict):
                if "time_major" in config:
                    config.pop("time_major")
                for k, v in config.items():
                    config[k] = recursive_clean(v)
                return config
            elif isinstance(config, list):
                return [recursive_clean(x) for x in config]
            else:
                return config

        model_dir = self.model_base / city
        fs_keras = model_dir / "gru.keras"
        fs_scaler = model_dir / "scaler.pkl"

        # ============================
        # LOAD TỪ FILESYSTEM
        # ============================
        if fs_keras.exists() and fs_scaler.exists():
            scaler = joblib.load(fs_scaler)

            # Đọc config trước để patch
            raw_model = keras.models.load_model(
                fs_keras,
                custom_objects={
                    "GRU": patched_gru,
                    "Bidirectional": patched_bidirectional,
                },
                compile=False
            )

            cfg = raw_model.get_config()
            cfg = recursive_clean(cfg)

            model = keras.Model.from_config(cfg, custom_objects={
                "GRU": patched_gru,
                "Bidirectional": patched_bidirectional
            })

            return ModelArtifacts(scaler=scaler, model=model)

        # ============================
        # LOAD TỪ MONGODB
        # ============================
        doc = self.db.models.find_one({"province": city})
        if not doc or not doc.get("keras_bytes") or not doc.get("scaler_bytes"):
            raise ApiError("model_not_trained", 400, "model_not_trained")

        keras_bytes = bytes(doc["keras_bytes"])
        scaler_bytes = bytes(doc["scaler_bytes"])

        scaler = joblib.load(BytesIO(scaler_bytes))

        raw_model = keras.models.load_model(
            BytesIO(keras_bytes),
            custom_objects={
                "GRU": patched_gru,
                "Bidirectional": patched_bidirectional,
            },
            compile=False
        )

        cfg = raw_model.get_config()
        cfg = recursive_clean(cfg)

        model = keras.Model.from_config(cfg, custom_objects={
            "GRU": patched_gru,
            "Bidirectional": patched_bidirectional
        })

        return ModelArtifacts(scaler=scaler, model=model)

    # ==============================================================
    # REALTIME
    # ==============================================================
    def get_realtime(self, city: str) -> Dict[str, Any]:
        doc = self.db.weather.find({"province": city}).sort("timestamp", -1).limit(1)
        latest = next(iter(doc), None)
        if not latest:
            raise ApiError("no_data_for_city", 404, "no_data_for_city")

        latest.pop("_id", None)
        return latest

    # ==============================================================
    # FORECAST (Keras)
    # ==============================================================
    def get_forecast(self, city: str) -> Dict[str, Any]:
        rows = self.get_recent_series(city, SEQ_IN)
        if len(rows) < SEQ_IN:
            raise ApiError("not_enough_data", 400, "not_enough_data")

        # Build matrix
        Xdf = [[float(r.get(k, 0.0)) for k in FEATURES] for r in rows]

        # Load artifacts
        artifacts = self._load_model_artifacts(city)
        scaler = artifacts.scaler
        model = artifacts.model

        # Normalize
        X_scaled = scaler.transform(np.array(Xdf))
        Xin = np.expand_dims(X_scaled, 0).astype("float32")

        # Predict 6 bước
        y = model.predict(Xin)[0]

        temps = []
        for v in y:
            vec = np.zeros((1, len(FEATURES)))
            vec[0, 0] = float(v)
            inv = scaler.inverse_transform(vec)[0]
            temps.append(float(inv[0]))

        steps = [f"+{i}h" for i in range(1, 7)]

        history = self.get_recent_series(city, 48)
        history_payload = {
            "labels": [h.get("timestamp") for h in history],
            "temp": [h.get("temp") for h in history],
            "humidity": [h.get("humidity") for h in history],
            "rain": [h.get("rain") for h in history],
        }

        return {
            "city": city,
            "prediction_steps": steps,
            "temp": temps,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "history": history_payload,
        }

    # ==============================================================
    # DASHBOARD
    # ==============================================================
    def get_dashboard(self, city: Optional[str] = None) -> Dict[str, Any]:
        city = city or (self.list_cities()[0] if self.list_cities() else self.cfg.CITY)

        realtime = self.get_realtime(city)
        forecast = self.get_forecast(city)
        dataset_history = self.get_dataset_history(city, 25)
        latest_dataset = dataset_history[0] if dataset_history else None
        provinces = self.list_cities()

        return {
            "city": city,
            "realtime": realtime,
            "forecast": forecast,
            "dataset_history": dataset_history,
            "dataset_summary": latest_dataset,
            "provinces": provinces,
        }
