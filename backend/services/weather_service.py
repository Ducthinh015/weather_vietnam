from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
from io import BytesIO

import numpy as np
import joblib
from tensorflow import keras
from pymongo.collection import Collection

try:
    import tflite_runtime.interpreter as tflite
except Exception:
    tflite = None

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
    keras_model: Any     # keras loaded
    interpreter: Any     # tflite interpreter or None


class WeatherService:
    def __init__(self):
        self.cfg = Config()
        self.db = get_db()
        self._pkg_root = Path(__file__).resolve().parents[1]

        self.model_base = self._pkg_root / "models" / "weather"
        self._data_dir = self._pkg_root / "data"

    # =============================================================
    # Cities helper
    # =============================================================
    def list_cities(self) -> List[str]:
        fp = self._data_dir / "cities.json"
        if fp.exists():
            try:
                raw = json.loads(fp.read_text())
                cities = raw.get("cities", raw)
                return [c for c in cities if isinstance(c, str)]
            except:
                pass

        raw = getattr(self.cfg, "CITIES", "")
        if raw:
            return [c.strip() for c in raw.split(",")]

        return [self.cfg.CITY]

    # =============================================================
    # Dataset history
    # =============================================================
    def get_dataset_history(self, city: Optional[str] = None, limit: int = 100):
        coll: Collection = self.db.dataset_history
        q = {"city": city} if city else {}
        cursor = coll.find(q).sort("snapshot_at", -1).limit(limit)

        out = []
        for doc in cursor:
            doc["id"] = str(doc.pop("_id", ""))
            out.append(doc)
        return out

    # =============================================================
    # Recent series
    # =============================================================
    def get_recent_series(self, city: str, limit: int = 48):
        cursor = (
            self.db.weather
            .find({"province": city}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
        return list(cursor)[::-1]

    # =============================================================
    # LOAD MODEL (Filesystem + Mongo fallback)
    # =============================================================
    def _load_model_artifacts(self, city: str) -> ModelArtifacts:
        model_dir = self.model_base / city

        fs_keras = model_dir / "gru.keras"
        fs_tflite = model_dir / "model.tflite"
        fs_scaler = model_dir / "scaler.pkl"

        # ---- 1) Prefer local filesystem  ----
        if fs_scaler.exists():
            scaler = joblib.load(fs_scaler)
        else:
            scaler = None

        keras_model = None
        if fs_keras.exists():
            try:
                keras_model = keras.models.load_model(fs_keras, compile=False)
            except Exception:
                keras_model = None

        interpreter = None
        if fs_tflite.exists() and tflite is not None:
            try:
                interpreter = tflite.Interpreter(model_path=str(fs_tflite))
                interpreter.allocate_tensors()
            except Exception:
                interpreter = None

        # If filesystem OK → return immediately
        if scaler and (keras_model or interpreter):
            return ModelArtifacts(
                scaler=scaler,
                keras_model=keras_model,
                interpreter=interpreter
            )

        # ---- 2) MongoDB fallback ----
        doc = self.db.models.find_one({"province": city})
        if not doc:
            raise ApiError("model_not_found", 404, "model_not_found")

        if scaler is None and doc.get("scaler_bytes"):
            scaler = joblib.load(BytesIO(bytes(doc["scaler_bytes"])))

        if keras_model is None and doc.get("keras_bytes"):
            keras_model = keras.models.load_model(
                BytesIO(bytes(doc["keras_bytes"])),
                compile=False
            )

        return ModelArtifacts(
            scaler=scaler,
            keras_model=keras_model,
            interpreter=None
        )

    # =============================================================
    # REALTIME
    # =============================================================
    def get_realtime(self, city: str):
        cur = self.db.weather.find({"province": city}).sort("timestamp", -1).limit(1)
        row = next(iter(cur), None)
        if not row:
            raise ApiError("no_data_for_city", 404, "no_data_for_city")
        row.pop("_id", None)
        return row

 
    def get_forecast(self, city: str):
        rows = self.get_recent_series(city, SEQ_IN)
        if len(rows) < SEQ_IN:
            raise ApiError("not_enough_data", 400, "not_enough_data")

        # Build matrix
        Xdf = [[float(r.get(k, 0.0)) for k in FEATURES] for r in rows]

        artifacts = self._load_model_artifacts(city)
        scaler = artifacts.scaler

        # Normalize input
        X_scaled = scaler.transform(np.array(Xdf))
        Xin = np.expand_dims(X_scaled, 0).astype("float32")

        # ---- 1) Try TFLite first ----
        if artifacts.interpreter:
            intr = artifacts.interpreter
            intr.allocate_tensors()

            input_details = intr.get_input_details()
            output_details = intr.get_output_details()

            intr.set_tensor(input_details[0]["index"], Xin)
            intr.invoke()
            y_scaled = intr.get_tensor(output_details[0]["index"])[0]

        else:
            if artifacts.keras_model is None:
                raise ApiError("no_model_available", 500, "no_model_available")

            y_scaled = artifacts.keras_model.predict(Xin)[0]


        y_scaled_2d = y_scaled.reshape(1, -1)
        y = scaler.inverse_transform(y_scaled_2d)[0]

        # Build forecast
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
            "temp": list(map(float, y)),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "history": history_payload,
        }

    def get_dashboard(self, city: Optional[str] = None):
        city = city or self.list_cities()[0]

        realtime = self.get_realtime(city)
        forecast = self.get_forecast(city)
        dataset_history = self.get_dataset_history(city, 25)
        latest_dataset = dataset_history[0] if dataset_history else None

        return {
            "city": city,
            "realtime": realtime,
            "forecast": forecast,
            "dataset_history": dataset_history,
            "dataset_summary": latest_dataset,
            "provinces": self.list_cities(),
        }
