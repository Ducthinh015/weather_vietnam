from typing import Iterable
import pandas as pd
from pmdarima import auto_arima
from statsmodels.tsa.arima.model import ARIMA

def fit_arima_and_predict(series: Iterable, future_points: int = 5):
    s = pd.Series(series)
    model_sel = auto_arima(s, trace=False, suppress_warnings=True)
    order = model_sel.get_params().get("order")
    model = ARIMA(s, order=order)
    fit = model.fit()
    start = len(s)
    end = start + future_points - 1
    pred = fit.predict(start=start, end=end, typ="levels")
    return pred

def predict_arima_111(series: Iterable, steps: int = 3):
    s = pd.Series(series).astype(float)
    model = ARIMA(s, order=(1, 1, 1))
    fit = model.fit()
    fc = fit.forecast(steps=steps)
    return [float(x) for x in fc]

