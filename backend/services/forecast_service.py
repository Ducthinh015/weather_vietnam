from typing import Dict, Any, List
import pandas as pd
import warnings
from ..models.arima_model import fit_arima_and_predict


def forecast_next_hours(hourly_payload: Dict[str, Any], hours: int = 5) -> List[Dict[str, Any]]:
    # Prepare temperature and humidity arrays from OneCall hourly
    hourly = hourly_payload.get("hourly", [])
    temperature = []
    humidity = []
    for i in range(min(48, len(hourly))):
        h = hourly[i]
        temperature.append(h.get("temp", 273) - 273)  # convert to C from K
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
