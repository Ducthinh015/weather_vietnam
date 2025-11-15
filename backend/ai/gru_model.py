import os
import numpy as np
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import GRU, Dense
from tensorflow.keras.optimizers import Adam


def build_gru(seq_len: int, feature_count: int, out_steps: int = 6):
    m = Sequential([
        GRU(64, return_sequences=True, input_shape=(seq_len, feature_count)),
        GRU(32),
        Dense(out_steps * feature_count)
    ])
    m.compile(optimizer=Adam(), loss="mse")
    return m


def save_model(model, path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    model.save(path)


def load_gru(path: str):
    return load_model(path)
