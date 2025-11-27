from __future__ import annotations

import json
import numpy as np
import joblib
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List
from pymongo.collection import Collection
import tensorflow as tf
from tensorflow import keras

from backend.db import get_db
from backend.utils.responses import ApiError
from backend.config import Config

FEATURES = ["temp", "humidity", "pressure", "wind_speed", "cloud", "rain"]
SEQ_IN = 48
SEQ_OUT = 6


@dataclass
class ModelArtifacts:
    scaler: Any
    model: keras.Model


class WeatherService:
    def __init__(self):
        self.cfg = Config()
        self.db = get_db()
        self._pkg_root = Path(__file__).resolve().parents[1]
        self.model_base = self._pkg_root / "models" / "weather"

    # =========================================================
    # REMOVE invalid keys (e.g. time_major) in GRU config
    # =========================================================
    def clean_layer_config(self, cfg: Dict) -> Dict:
        remove_keys = ["time_major"]

        if isinstance(cfg, dict):
            keys_to_remove = [k for k in cfg.keys() if k in remove_keys]
            for k in keys_to_remove:
                cfg.pop(k)

            for v in cfg.values():
                self.clean_layer_config(v)

        elif isinstance(cfg, list):
            for v in cfg:
                self.clean_layer_config(v)

        return cfg

    # =========================================================
    # LOAD MODEL FIXED
    # =========================================================
    def _load_model_artifacts(self, city: str) -> ModelArtifacts:
        model_dir = self.model_base / city

        keras_path = model_dir / "gru.keras"
        scaler_path = model_dir / "scaler.pkl"

        if not keras_path.exists():
            raise ApiError("model_not_found", f"No Keras model for {city}")

        # --- load model as config ---
        raw_model = keras.models.load_model(
            keras_path,
            compile=False  # disable compile for safety
        )

        config = raw_model.get_config()

        # sanitize config
        config = self.clean_layer_config(config)

        # rebuild model
        fixed_model = keras.Model.from_config(config)

        # load weights (if saved separately we load .weights.h5)
        weights_path = model_dir / "gru.weights.h5"
        if weights_path.exists():
            fixed_model.load_weights(weights_path)  
        else:
            # weights embedded inside .keras
            pass

        # load scaler
        if not scaler_path.exists():
            raise ApiError("scaler_not_found", f"No scaler.pkl for {city}")

        scaler = joblib.load(scaler_path)

        return ModelArtifacts(scaler=scaler, model=fixed_model)

    # =========================================================
    # FETCH HISTORY
    # =========================================================
    def get_last_48h(self, city: str):
        cursor = (
            self.db.weather
            .find({"province": city}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(48)
        )
        return list(cursor)[::-1]

    # =========================================================
    # FORECAST
    # =========================================================
    def get_forecast(self, city: str):
        artifacts = self._load_model_artifacts(city)

        last48 = self.get_last_48h(city)
        if len(last48) < SEQ_IN:
            raise ApiError("not_enough_data", "Need 48h data to forecast")

        seq = np.array([[row[f] for f in FEATURES] for row in last48], dtype=float)

        X = artifacts.scaler.transform(seq)
        X = np.expand_dims(X, axis=0)

        pred = artifacts.model.predict(X)[0]
        pred = artifacts.scaler.inverse_transform(pred)

        out = []
        for i, val in enumerate(pred):
            out.append({
                "t_plus": i + 1,
                "temp": float(val[0]),
                "humidity": float(val[1]),
                "pressure": float(val[2]),
                "wind_speed": float(val[3]),
                "cloud": float(val[4]),
                "rain": float(val[5]),
            })

        return out

    # =========================================================
    # REALTIME
    # =========================================================
    def get_realtime(self, city: str):
        d = (
            self.db.weather
            .find_one({"province": city}, {"_id": 0}, sort=[("timestamp", -1)])
        )
        return d

    # =========================================================
    # DASHBOARD
    # =========================================================
    def get_dashboard(self, city: str):
        realtime = self.get_realtime(city)
        history = self.get_last_48h(city)
        forecast = self.get_forecast(city)

        return {
            "realtime": realtime,
            "history": history,
            "forecast": forecast,
        }
