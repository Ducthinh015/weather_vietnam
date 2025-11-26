import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone
from io import BytesIO

import numpy as np
import pandas as pd
from dateutil import parser
from bson.binary import Binary

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import GRU, Dense, Input, Bidirectional
from tensorflow.keras.optimizers import Adam
from tensorflow.keras import backend as K

from sklearn.preprocessing import MinMaxScaler
import joblib

from backend.db import get_db


# ==========================
# CONFIG
# ==========================
FEATURES = ["temp", "humidity", "wind_kph", "rain_mm", "cloud", "uv"]
SEQ_IN = 48      # 48 giờ
SEQ_OUT = 6      # dự đoán 6 giờ tiếp theo

MIN_SAMPLES = 200      # tối thiểu 200 mẫu để train
MIN_COVERAGE_HOURS = 0  # không kiểm coverage


# ==========================
# PARSE TIME
# ==========================
def to_dt(v):
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return parser.parse(v)
        except:
            return None
    return None


# ==========================
# LOAD DATA 1 CITY
# ==========================
def load_city_data(city: str) -> Optional[pd.DataFrame]:
    db = get_db()

    rows = list(
        db.weather.find({"province": city}, {"_id": 0}).sort("timestamp", 1)
    )

    if not rows or len(rows) < MIN_SAMPLES:
        return None

    df = pd.DataFrame(rows)

    # clean
    df = df.dropna(subset=FEATURES)
    df["timestamp"] = df["timestamp"].apply(to_dt)
    df = df[df["timestamp"].notnull()]
    df = df.sort_values("timestamp")

    return df.tail(2000)   # tối đa 2000 mẫu mới nhất


# ==========================
# TRAIN 1 CITY
# ==========================
def build_and_train(city: str) -> str:
    df = load_city_data(city)
    if df is None or len(df) < MIN_SAMPLES:
        return f"[Skip] {city} dataset < {MIN_SAMPLES} samples"

    # scale
    data = df[FEATURES].astype(float).values
    scaler = MinMaxScaler().fit(data)
    scaled = scaler.transform(data)

    # tạo sequence
    X, Y = [], []
    for i in range(len(scaled) - SEQ_IN - SEQ_OUT):
        X.append(scaled[i:i + SEQ_IN])
        Y.append(scaled[i + SEQ_IN:i + SEQ_IN + SEQ_OUT, 0])  # predict temp

    if not X:
        return f"[Skip] {city} not enough windows"

    X, Y = np.array(X), np.array(Y)

    # model
    model = Sequential([
        Input(shape=(SEQ_IN, len(FEATURES))),
        Bidirectional(GRU(128, return_sequences=True, dropout=0.2)),
        GRU(128, return_sequences=True, dropout=0.2),
        GRU(64, dropout=0.2),
        Dense(64, activation="relu"),
        Dense(32, activation="relu"),
        Dense(SEQ_OUT),
    ])

    model.compile(optimizer=Adam(0.0005), loss="mse", metrics=["mae"])
    model.fit(X, Y, epochs=10, batch_size=16, verbose=0)

    # ================================
    # TFLITE CONVERSION (FIXED)
    # ================================
    converter = tf.lite.TFLiteConverter.from_keras_model(model)

    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS,
        tf.lite.OpsSet.SELECT_TF_OPS
    ]
    converter._experimental_lower_tensor_list_ops = False
    converter.optimizations = [tf.lite.Optimize.DEFAULT]

    tflite_model = converter.convert()

    # save files
    out_dir = Path("backend/models/weather") / city
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "model.tflite", "wb") as f:
        f.write(tflite_model)

    buf = BytesIO()
    joblib.dump(scaler, buf)
    with open(out_dir / "scaler.pkl", "wb") as f:
        f.write(buf.getvalue())

    # save metadata DB
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    db.models.replace_one(
        {"province": city},
        {
            "province": city,
            "trained_at": now,
            "samples_used": len(df),
            "seq_in": SEQ_IN,
            "seq_out": SEQ_OUT,
            "features": FEATURES,
            "tflite_bytes": Binary(tflite_model),
            "scaler_bytes": Binary(buf.getvalue()),
        },
        upsert=True,
    )

    # clean
    try:
        del model, X, Y
    except:
        pass
    K.clear_session()

    return f"[OK] {city} ({len(df)} samples)"


# ==========================
# LOAD CITIES
# ==========================
def _load_cities() -> List[str]:
    cities_file = Path("backend/data/cities.json")
    if cities_file.exists():
        import json
        try:
            data = json.loads(cities_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            if "cities" in data:
                return data["cities"]
        except:
            pass

    raise RuntimeError("No cities found in cities.json")


# ==========================
# TRAIN ALL
# ==========================
def train_all_sequential():
    for c in _load_cities():
        print(build_and_train(c))


if __name__ == "__main__":
    train_all_sequential()
