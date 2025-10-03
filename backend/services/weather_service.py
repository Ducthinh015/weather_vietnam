import requests
from typing import Dict, Any
from ..utils.cache import cache_get, cache_set

BASE_URL = "https://api.openweathermap.org/data/2.5"


def get_current_weather(city: str, api_key: str) -> Dict[str, Any]:
    cache_key = f"current:{city.lower()}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    resp = requests.get(f"{BASE_URL}/weather", params={"q": city, "appid": api_key, "units": "metric"})
    resp.raise_for_status()
    data = resp.json()
    cache_set(cache_key, data)
    return data


def get_hourly_48h(lat: float, lon: float, api_key: str) -> Dict[str, Any]:
    cache_key = f"hourly:{lat:.4f},{lon:.4f}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    resp = requests.get(f"{BASE_URL}/onecall", params={"lat": lat, "lon": lon, "appid": api_key})
    resp.raise_for_status()
    data = resp.json()
    cache_set(cache_key, data)
    return data
