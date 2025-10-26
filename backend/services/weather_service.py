import requests
from typing import Dict, Any, List, Tuple
from ..utils.cache import cache_get, cache_set
import os
import json
import unicodedata

BASE_URL = "https://api.weatherapi.com/v1"

def get_current_weather(city: str, api_key: str) -> Dict[str, Any]:
    cache_key = f"wa:current:{city.lower()}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    resp = requests.get(
        f"{BASE_URL}/current.json",
        params={"key": api_key, "q": city, "lang": "vi"},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    cache_set(cache_key, data)
    return data

def get_forecast_daily(city: str, days: int, api_key: str) -> Dict[str, Any]:
    cache_key = f"wa:forecast:{city.lower()}:{days}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    resp = requests.get(
        f"{BASE_URL}/forecast.json",
        params={
            "key": api_key,
            "q": city,
            "days": days,
            "aqi": "no",
            "alerts": "no",
            "lang": "vi",
        },
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    cache_set(cache_key, data)
    return data

def extract_hourly_series(forecast: Dict[str, Any]) -> Tuple[List[float], List[float]]:
    temps: List[float] = []
    hums: List[float] = []
    for day in forecast.get("forecast", {}).get("forecastday", []):
        for h in day.get("hour", []):

            if h.get("temp_c") is not None:
                temps.append(float(h.get("temp_c")))
                hums.append(float(h.get("humidity", 0)))
    return temps, hums

def get_forecast_data(city: str, hours: int = 5) -> Dict[str, Any]:
    try:
        key = os.getenv("WEATHERAPI_KEY")

        def _norm(s: str) -> str:
            if not s:
                return ""
            nf = unicodedata.normalize('NFD', s)
            no_acc = ''.join(ch for ch in nf if unicodedata.category(ch) != 'Mn')
            return no_acc.lower().strip()

        vn_loc_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'vn_locations.json')
        latlon_q = None
        try:
            with open(vn_loc_path, 'r', encoding='utf-8') as f:
                locs = json.load(f)
            norm_city = _norm(city)
            for loc in locs:
                if _norm(loc.get('alias')) == norm_city or _norm(loc.get('name')) == norm_city:
                    latlon_q = f"{loc.get('lat')},{loc.get('lon')}"
                    break
        except Exception:
            pass

        def call_forecast(q: str) -> requests.Response:
            return requests.get(
                f"{BASE_URL}/forecast.json",
                params={"key": key, "q": q, "days": 1, "lang": "vi"},
                timeout=20,
            )

        tried = []
        candidates = []
        if latlon_q:
            candidates.append(latlon_q)
        candidates.extend((f"{city},VN", city, f"{city}, Vietnam"))
        for q in candidates:
            tried.append(q)
            res = call_forecast(q)
            if res.status_code == 200:
                data = res.json()
                break
        else:

            sres = requests.get(f"{BASE_URL}/search.json", params={"key": key, "q": city}, timeout=15)
            if sres.status_code == 200 and sres.json():
                top = sres.json()[0]
                query = f"{top.get('lat')},{top.get('lon')}"
                tried.append(query)
                res = call_forecast(query)
                if res.status_code == 200:
                    data = res.json()
                else:
                    return {"error": "weatherapi_forecast_failed", "status": res.status_code, "detail": res.text, "tried": tried}
            else:
                return {"error": "weatherapi_search_failed", "status": sres.status_code, "detail": sres.text}

        hourly = ((data.get("forecast", {}) or {}).get("forecastday") or [{}])[0].get("hour", [])
        if not hourly:
            cur = data.get("current", {}) or {}
            return {
                "forecast": [
                    {"time": f"t+{i}h", "temp_c": cur.get("temp_c", 0), "humidity": cur.get("humidity", 0)}
                    for i in range(hours)
                ],
                "fallback": True,
            }

        from datetime import datetime
        try:
            loc_now_str = ((data.get("location") or {}).get("localtime")) 
            if loc_now_str:
                now_local = datetime.strptime(loc_now_str, "%Y-%m-%d %H:%M")
            else:
                now_local = datetime.utcnow()
            base = now_local.replace(minute=0, second=0, microsecond=0)
            sel = []
            for h in hourly:
                ts = h.get("time") 
                try:
                    ht = datetime.strptime(ts, "%Y-%m-%d %H:%M") if ts else None
                except Exception:
                    ht = None
                if ht is None or ht >= base:
                    sel.append(h)
            if len(sel) < hours:
                sel = hourly[-hours:]
        except Exception:
            sel = hourly[:hours]

        forecast = [
            {"time": h.get("time"), "temp_c": h.get("temp_c"), "humidity": h.get("humidity")}
            for h in sel[:hours]
        ]
        return {"forecast": forecast, "fallback": False}
    except Exception as e:
        return {"error": "weatherapi_exception", "detail": str(e)}

def get_current_resolved(city: str) -> Dict[str, Any]:
    try:
        key = os.getenv("WEATHERAPI_KEY")

        def _norm(s: str) -> str:
            if not s:
                return ""
            nf = unicodedata.normalize('NFD', s)
            no_acc = ''.join(ch for ch in nf if unicodedata.category(ch) != 'Mn')
            return no_acc.lower().strip()

        vn_loc_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'vn_locations.json')
        latlon_q = None
        try:
            with open(vn_loc_path, 'r', encoding='utf-8') as f:
                locs = json.load(f)
            norm_city = _norm(city)
            for loc in locs:
                if _norm(loc.get('alias')) == norm_city or _norm(loc.get('name')) == norm_city:
                    latlon_q = f"{loc.get('lat')},{loc.get('lon')}"
                    break
        except Exception:
            pass

        def call_current(q: str) -> requests.Response:
            return requests.get(
                f"{BASE_URL}/current.json",
                params={"key": key, "q": q, "lang": "vi"},
                timeout=20,
            )

        candidates = []
        if latlon_q:
            candidates.append(latlon_q)
        candidates.extend((f"{city},VN", city, f"{city}, Vietnam"))
        for q in candidates:
            r = call_current(q)
            if r.status_code == 200:
                return r.json()

        sres = requests.get(f"{BASE_URL}/search.json", params={"key": key, "q": city}, timeout=15)
        if sres.status_code == 200 and sres.json():
            top = sres.json()[0]
            query = f"{top.get('lat')},{top.get('lon')}"
            r = call_current(query)
            if r.status_code == 200:
                return r.json()
            return {"error": "weatherapi_current_failed", "status": r.status_code, "detail": r.text}
        return {"error": "weatherapi_search_failed", "status": sres.status_code, "detail": sres.text}
    except Exception as e:
        return {"error": "weatherapi_exception", "detail": str(e)}

