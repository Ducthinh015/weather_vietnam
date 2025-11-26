from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Optional, List

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import GRU, Dense, Input, Bidirectional
from tensorflow.keras.optimizers import Adam
from tensorflow.keras import backend as K
import tensorflow as tf
import joblib
from io import BytesIO
from bson.binary import Binary
from datetime import datetime, timezone
from dateutil import parser

import os
from backend.config import Config
from backend.db import get_db


# ===========================
# CONFIG
# ===========================
FEATURES = ["temp", "humidity", "wind_kph", "rain_mm", "cloud", "uv"]

SEQ_IN = 48
SEQ_OUT = 6

TARGET_SAMPLES = int(os.getenv("MIN_TRAIN_SAMPLES", "10"))
MIN_COVERAGE_HOURS = float(os.getenv("MIN_TRAIN_HOURS", "0"))

EPOCHS = 10
BATCH_SIZE = 16


# ===========================
# UTIL: PARSE TIMESTAMP
# ===========================
def _to_datetime(value):
    """Parse bất kỳ dạng timestamp nào từ MongoDB."""
    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        try:
            return parser.parse(value)
        except Exception:
            return None

    return None


# ===========================
# LOAD DATA CITY
# ===========================
def load_city_data(city: str) -> Optional[pd.DataFrame]:
    db = get_db()

    # ❗ FIX 1 – SORT đúng theo timestamp_utc
    rows = list(
        db.weather.find({"province": city}, {"_id": 0}).sort("timestamp_utc", 1)
    )

    if not rows or len(rows) < TARGET_SAMPLES:
        return None

    df = pd.DataFrame(rows).tail(TARGET_SAMPLES)

    # ❗ FIX 2 – lấy đúng field timestamp hoặc timestamp_utc
    first_ts = _to_datetime(
        df.iloc[0].get("timestamp") or df.iloc[0].get("timestamp_utc")
    )
    last_ts = _to_datetime(
        df.iloc[-1].get("timestamp") or df.iloc[-1].get("timestamp_utc")
    )

    if not first_ts or not last_ts:
        return None

    coverage = (last_ts - first_ts).total_seconds() / 3600.0
    if coverage < MIN_COVERAGE_HOURS:
        return None

    return df


# ===========================
# TRAIN 1 CITY
# ===========================
def build_and_train(city: str) -> str:
    df = load_city_data(city)
    if df is None:
        return f"[Skip] {city} dataset < {TARGET_SAMPLES} samples or < {MIN_COVERAGE_HOURS}h"

    # Chuẩn hóa data
    data = df[FEATURES].astype(float).values
    scaler = MinMaxScaler().fit(data)
    scaled = scaler.transform(data)

    X, Y = [], []
    horizon = SEQ_OUT
    target_idx = 0  # predict temp

    for i in range(len(scaled) - SEQ_IN - horizon):
        X.append(scaled[i:i + SEQ_IN])
        Y.append([scaled[i + SEQ_IN + j][target_idx] for j in range(horizon)])

    if not X:
        return f"[Skip] {city} not enough windows"

    X, Y = np.array(X), np.array(Y)

    # Model GRU
    model = Sequential([
        Input(shape=(SEQ_IN, len(FEATURES))),
        Bidirectional(GRU(128, return_sequences=True, dropout=0.2)),
        GRU(128, return_sequences=True, dropout=0.2),
        GRU(64, dropout=0.2),
        Dense(64, activation="relu"),
        Dense(32, activation="relu"),
        Dense(SEQ_OUT),
    ])

    model.compile(optimizer=Adam(learning_rate=0.0005), loss="mse", metrics=["mae"])
    model.fit(X, Y, epochs=EPOCHS, batch_size=BATCH_SIZE, verbose=0)

    db = get_db()
    out_dir = Path("backend/models/weather") / city
    out_dir.mkdir(parents=True, exist_ok=True)

    # TFLite
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()

    with open(out_dir / "model.tflite", "wb") as f:
        f.write(tflite_model)

    # Save scaler
    buf = BytesIO()
    joblib.dump(scaler, buf)
    scaler_bytes = buf.getvalue()

    with open(out_dir / "scaler.pkl", "wb") as f:
        f.write(scaler_bytes)

    # ❗ FIX 3 – coverage tính đúng timestamp_utc
    first = _to_datetime(df.iloc[0].get("timestamp") or df.iloc[0].get("timestamp_utc"))
    last = _to_datetime(df.iloc[-1].get("timestamp") or df.iloc[-1].get("timestamp_utc"))
    coverage_hours = (last - first).total_seconds() / 3600.0

    now = datetime.now(timezone.utc).isoformat()

    # Lưu MongoDB
    db.models.replace_one(
        {"province": city},
        {
            "province": city,
            "tflite_bytes": Binary(tflite_model),
            "scaler_bytes": Binary(scaler_bytes),
            "trained_at": now,
            "samples_used": len(df),
            "coverage_hours": coverage_hours,
            "seq_in": SEQ_IN,
            "seq_out": SEQ_OUT,
            "features": FEATURES,
        },
        upsert=True,
    )

    # Cleanup RAM
    try:
        del model, X, Y, data, scaled
    except:
        pass
    K.clear_session()
    import gc
    gc.collect()

    return f"[OK] {city}"


# ===========================
# LOAD LIST CITY
# ===========================
def _load_cities() -> List[str]:
    cfg = Config()
    import json

    cities_file = Path("backend/data/cities.json")
    if cities_file.exists():
        try:
            return json.loads(cities_file.read_text(encoding="utf-8"))
        except:
            pass

    raw = getattr(cfg, "CITIES", "")
    if raw:
        return [c.strip() for c in raw.split(",") if c.strip()]

    return []


# ===========================
# TRAIN ALL
# ===========================
def train_all_sequential():
    cities = _load_cities()
    if not cities:
        print("[WARN] No cities configured for training")
        return
    for c in cities:
        print(build_and_train(c))


def train_all_parallel(max_workers: int = 4):
    cities = _load_cities()
    if not cities:
        print("[WARN] No cities configured for training")
        return
    with ProcessPoolExecutor(max_workers=max_workers) as exe:
        for r in exe.map(build_and_train, cities):
            print(r)


def train_all():
    train_all_parallel(max_workers=4)


if __name__ == "__main__":
    train_all_sequential()
