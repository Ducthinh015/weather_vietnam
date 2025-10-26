from typing import Dict, Any, List
import pandas as pd
import warnings
from ..models.arima_model import fit_arima_and_predict

def forecast_next_hours(hourly_payload: Dict[str, Any], hours: int = 5) -> List[Dict[str, Any]]:

    hourly = hourly_payload.get("hourly", [])
    temperature = []
    humidity = []
    for i in range(min(48, len(hourly))):
        h = hourly[i]
        temperature.append(h.get("temp", None)) 
        humidity.append(h.get("humidity", 0))

    dict_data = {"hours": list(range(len(temperature)))[::-1], "temp": temperature, "hum": humidity}
    df = pd.DataFrame(dict_data).dropna()
    temp_series = df["temp"]
    hum_series = df["hum"]

    warnings.filterwarnings("ignore")

    temp_pred = fit_arima_and_predict(temp_series, future_points=hours)
    hum_pred = fit_arima_and_predict(hum_series, future_points=hours)

    result = []
    for i in range(hours):
        result.append({
            "after_hours": i + 1,
            "temperature": round(float(temp_pred[i]), 1),
            "humidity": round(float(hum_pred[i]), 1)
        })
    return result

def forecast_from_series(temperatures: List[float], humidities: List[float], hours: int = 5) -> List[Dict[str, Any]]:
    dict_data = {"idx": list(range(len(temperatures))), "temp": temperatures, "hum": humidities}
    df = pd.DataFrame(dict_data).dropna()
    if df.empty:
        return []
    temp_series = df["temp"].astype(float)
    hum_series = df["hum"].astype(float)

    warnings.filterwarnings("ignore")
    temp_pred = fit_arima_and_predict(temp_series, future_points=hours)
    hum_pred = fit_arima_and_predict(hum_series, future_points=hours)

    out: List[Dict[str, Any]] = []
    for i in range(hours):
        out.append({
            "after_hours": i + 1,
            "temperature": round(float(temp_pred[i]), 1),
            "humidity": round(float(hum_pred[i]), 1),
        })
    return out

