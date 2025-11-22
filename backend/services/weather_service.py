from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional
import json
from io import BytesIO

import joblib
import numpy as np
from pymongo.collection import Collection

from backend.config import Config
from backend.db import get_db
from backend.utils.responses import ApiError

FEATURES = ["temp", "humidity", "pressure", "wind_speed", "cloud", "rain"]
SEQ_IN = 48
SEQ_OUT = 6


@dataclass
class ModelArtifacts:
    scaler: Any
    model: Any


class WeatherService:
    def __init__(self):
        self.cfg = Config()
        self.db = get_db()
        self.model_base = Path("backend/models/weather")

    # ------------------------------------------------------------------
    # Cities & dataset helpers
    # ------------------------------------------------------------------
    def list_cities(self) -> List[str]:
        cities_fp = Path("backend/data/cities.json")
        if cities_fp.exists():
            try:
                return json.loads(cities_fp.read_text(encoding="utf-8"))
            except Exception:
                pass
        raw = getattr(self.cfg, "CITIES", "") or ""
        if raw:
            return [c.strip() for c in raw.split(",") if c.strip()]
        return [self.cfg.CITY]

    def get_dataset_history(self, city: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        coll: Collection = self.db.dataset_history
        query: Dict[str, Any] = {}
        if city:
            query["city"] = city
        cursor = coll.find(query).sort("snapshot_at", -1).limit(limit)
        items: List[Dict[str, Any]] = []
        for doc in cursor:
            doc["id"] = str(doc.pop("_id", ""))
            items.append(doc)
        return items

    def get_recent_series(self, city: str, limit: int = 48) -> List[Dict[str, Any]]:
        cursor = (
            self.db.weather
            .find({"province": city}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
        return list(cursor)[::-1]

    # ------------------------------------------------------------------
    # Mongo helpers
    # ------------------------------------------------------------------
    def _load_model_artifacts(self, city: str) -> ModelArtifacts:
        model_dir = self.model_base / city
        fs_model = model_dir / "gru.keras"
        fs_scaler = model_dir / "scaler.pkl"
        scaler = None
        model = None

        # Lazy import TensorFlow only when needed
        try:
            from tensorflow.keras.models import load_model  # type: ignore
        except Exception as exc:
            raise ApiError("ml_unavailable", status_code=501, error_code="ml_unavailable", details={"detail": str(exc)})

        if fs_model.exists() and fs_scaler.exists():
            # Keras 3 compatibility: allow loading legacy models
            model = load_model(str(fs_model), compile=False, safe_mode=False)
            scaler = joblib.load(fs_scaler)
            return ModelArtifacts(scaler=scaler, model=model)

        model_doc = self.db.models.find_one({"province": city, "model_bytes": {"$exists": True}})
        if model_doc and model_doc.get("scaler_bytes"):
            scaler_bytes = bytes(model_doc["scaler_bytes"])
            model_bytes = bytes(model_doc["model_bytes"])
        else:
            legacy_model = self.db.models.find_one({"model_name": f"{city}_gru.h5", "model_bytes": {"$exists": True}})
            legacy_scaler = self.db.models.find_one({"model_name": f"{city}_scaler.pkl"})
            if not legacy_model or not legacy_scaler:
                raise ApiError("model_not_trained", status_code=400, error_code="model_not_trained")
            model_bytes = bytes(legacy_model.get("model_bytes") or b"")
            scaler_bytes = bytes(legacy_scaler.get("scaler_bytes") or legacy_scaler.get("model_bytes") or b"")

        if not model_bytes or not scaler_bytes:
            raise ApiError("model_not_trained", status_code=400, error_code="model_not_trained")

        scaler = joblib.load(BytesIO(scaler_bytes))
        with NamedTemporaryFile(suffix=".keras") as tmp:
            Path(tmp.name).write_bytes(model_bytes)
            model = load_model(tmp.name, compile=False, safe_mode=False)
        return ModelArtifacts(scaler=scaler, model=model)

    # ------------------------------------------------------------------
    def get_realtime(self, city: str) -> Dict[str, Any]:
        doc = self.db.weather.find({"province": city}).sort("timestamp", -1).limit(1)
        latest = next(iter(doc), None)
        if not latest:
            raise ApiError("no_data_for_city", status_code=404, error_code="no_data")
        latest.pop("_id", None)
        return latest

    def get_forecast(self, city: str) -> Dict[str, Any]:
        rows = self.get_recent_series(city, limit=SEQ_IN)
        if len(rows) < SEQ_IN:
            raise ApiError("not_enough_data", status_code=400, error_code="not_enough_data")

        Xdf = [[float(r.get(k, 0.0)) for k in FEATURES] for r in rows]
        artifacts = self._load_model_artifacts(city)
        scaler = artifacts.scaler
        model = artifacts.model

        Xscaled = scaler.transform(np.array(Xdf))
        Xin = np.expand_dims(Xscaled, axis=0)
        pred = model.predict(Xin, verbose=0)[0]

        temps: List[float] = []
        if np.isscalar(pred) or (hasattr(pred, "shape") and pred.shape in {(), (1,)}):
            vec = np.zeros((1, len(FEATURES)))
            vec[0, 0] = float(pred if np.isscalar(pred) else pred[0])
            inv = scaler.inverse_transform(vec)[0]
            temps = [float(inv[0])]
        elif hasattr(pred, "ndim") and pred.ndim == 1 and pred.shape[0] == SEQ_OUT:
            for value in pred:
                vec = np.zeros((1, len(FEATURES)))
                vec[0, 0] = float(value)
                inv = scaler.inverse_transform(vec)[0]
                temps.append(float(inv[0]))
        else:
            horizon = pred.reshape(SEQ_OUT, len(FEATURES))
            inv = scaler.inverse_transform(horizon)
            temps = [float(v[0]) for v in inv]

        steps = [f"+{i}h" for i in range(1, len(temps) + 1)]
        history = self.get_recent_series(city, limit=48)
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

    def get_dashboard(self, city: Optional[str] = None) -> Dict[str, Any]:
        city = city or (self.list_cities()[0] if self.list_cities() else self.cfg.CITY)
        realtime = self.get_realtime(city)
        forecast = self.get_forecast(city)
        dataset_history = self.get_dataset_history(city=city, limit=25)
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
