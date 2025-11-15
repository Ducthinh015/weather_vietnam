from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import GRU, Dense
import joblib

from ..config import Config

DATA_DIR = Path("backend/data/weather")
MODEL_DIR = Path("backend/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = ["temp", "humidity", "pressure", "wind_speed", "cloud", "rain"]
SEQ_IN, SEQ_OUT = 48, 6


def load_city_data(city: str) -> Optional[pd.DataFrame]:
    file = DATA_DIR / f"{city}.json"
    if not file.exists():
        return None
    try:
        df = pd.read_json(file)
    except ValueError:
        try:
            import json
            df = pd.DataFrame(json.loads(file.read_text(encoding="utf-8")))
        except Exception:
            return None
    # First-train rule: require at least 500 samples
    if len(df) < 500:
        return None
    df = df.sort_values("timestamp")
    # Storage rule: only keep the latest 2000 samples to stabilize training size
    if len(df) > 2000:
        df = df.tail(2000)
    return df


def build_and_train(city: str) -> str:
    df = load_city_data(city)
    if df is None:
        return f"[Skip] {city} not enough data (need >=500)"

    data = df[FEATURES].astype(float).values

    scaler = MinMaxScaler().fit(data)
    scaled = scaler.transform(data)

    X, Y = [], []
    for i in range(len(scaled) - SEQ_IN - SEQ_OUT):
        X.append(scaled[i:i + SEQ_IN])
        Y.append(scaled[i + SEQ_IN:i + SEQ_IN + SEQ_OUT])
    if not X:
        return f"[Skip] {city} not enough windows"

    X, Y = np.array(X), np.array(Y)

    model = Sequential([
        GRU(64, return_sequences=True, input_shape=(SEQ_IN, len(FEATURES))),
        GRU(32),
        Dense(SEQ_OUT * len(FEATURES)),
    ])
    model.compile(optimizer="adam", loss="mse")
    model.fit(X, Y.reshape(len(Y), -1), epochs=30, batch_size=16, verbose=0)

    model.save(MODEL_DIR / f"{city}_gru.h5")
    joblib.dump(scaler, MODEL_DIR / f"{city}_scaler.pkl")

    return f"[OK] {city}"


def train_all():
    cfg = Config()
    # ưu tiên cities.json, fallback CITIES env
    from pathlib import Path
    import json
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
        print("[WARN] No cities configured for training")
        return

    with ProcessPoolExecutor(max_workers=6) as exe:
        results = exe.map(build_and_train, cities)

    for r in results:
        print(r)


if __name__ == "__main__":
    train_all()
