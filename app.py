import json
import unicodedata
from flask import Flask, request, jsonify, render_template, send_from_directory, Response
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import os
import random
from datetime import datetime, timedelta
import pandas as pd
from ml.lstm_predict import predict_next24h
from ml.irrigation_model import load_irrigation_model, predict_irrigation_action

# Flask
FRONTEND_DIR = os.path.join(os.getcwd(), 'frontend', 'src')
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# Load environment (.env)
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))
load_dotenv()  # also load root .env if present

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/farm_ai")
client = MongoClient(MONGO_URI)
db = client.get_database()

MODELS_DIR = os.path.join(os.getcwd(), 'models')
FORECAST_DIR = os.path.join(os.getcwd(), 'forecasts')
PLOTS_DIR = os.path.join(os.getcwd(), 'plots')
REPORTS_DIR = os.path.join(os.getcwd(), 'reports')
PER_CITY_DIR = os.path.join(MODELS_DIR, 'per_city')
VN_LOC_PATH = os.path.join(os.getcwd(), 'backend', 'data', 'vn_locations.json')
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(FORECAST_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(PER_CITY_DIR, exist_ok=True)


def _simulate_forecast(city: str, district: str, commune: str):
    """
    Fallback: tạo dữ liệu giả lập 24h để demo nếu chưa train LSTM.
    """
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    rows = []
    base_temp = 28.0
    for i in range(24):
        t = now + timedelta(hours=i)
        # Dao động nhiệt theo sóng sin ngày đêm
        temp = base_temp + 4*math.sin((i/24)*2*math.pi)
        hum = max(45, min(90, 65 + 20*math.sin((i/24)*2*math.pi + 1.0)))
        wind = 8 + 4*math.sin((i/24)*2*math.pi + 2.0)
        rain = max(0.0, 2*math.sin((i/24)*2*math.pi - 1.0))
        pres = 1005 + 5*math.sin((i/24)*2*math.pi - 0.5)
        rows.append({
            "datetime": t.strftime("%Y-%m-%d %H:00"),
            "temp": round(float(temp), 2),
            "humidity": round(float(hum), 1),
            "wind_speed": round(float(wind), 1),
            "rainfall": round(float(rain), 2),
            "pressure": round(float(pres), 1),
        })
    return rows


@app.route("/")
def index():
    # Serve the multi-page frontend index from frontend/src to unify UI on one port
    idx = os.path.join(FRONTEND_DIR, 'index.html')
    if os.path.exists(idx):
        return send_from_directory(FRONTEND_DIR, 'index.html')
    return render_template("index.html")


@app.route('/index.html')
def index_html():
    idx = os.path.join(FRONTEND_DIR, 'index.html')
    if os.path.exists(idx):
        return send_from_directory(FRONTEND_DIR, 'index.html')
    return render_template('index.html')


@app.route('/pages/<path:path>')
def serve_pages(path: str):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'pages'), path)


@app.route('/js/<path:path>')
def serve_js(path: str):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'js'), path)


@app.route('/styles/<path:path>')
def serve_styles(path: str):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'styles'), path)


@app.route('/assets/<path:path>')
def serve_assets(path: str):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'assets'), path)


@app.route('/favicon.ico')
def favicon():
    fav1 = os.path.join(FRONTEND_DIR, 'assets', 'favicon.ico')
    fav2 = os.path.join(FRONTEND_DIR, 'assets', 'favicon.png')
    if os.path.exists(fav1):
        return send_from_directory(os.path.join(FRONTEND_DIR, 'assets'), 'favicon.ico')
    if os.path.exists(fav2):
        return send_from_directory(os.path.join(FRONTEND_DIR, 'assets'), 'favicon.png')
    return Response(status=204)


@app.route("/locations")
def locations_api():
    """Trả về cấu trúc: { cities: [...], districts: {city:[...]}, communes: {"city|district":[...]}, crops: {"city|district|commune":[...]}}
    """
    locs = list(db.get_collection("locations").find({}, {"_id": 0}))
    cities = sorted({x.get("city") for x in locs if x.get("city")})
    districts = {}
    communes = {}
    crops = {}
    for x in locs:
        c = x.get("city"); d = x.get("district"); m = x.get("commune")
        districts.setdefault(c, set()).add(d)
        communes.setdefault(f"{c}|{d}", set()).add(m)
        crops[f"{c}|{d}|{m}"] = x.get("crops") or []
    districts = {k: sorted(list(v)) for k, v in districts.items()}
    communes = {k: sorted(list(v)) for k, v in communes.items()}
    return jsonify({"cities": cities, "districts": districts, "communes": communes, "crops": crops})


@app.route("/predict")
def predict():
    city = request.args.get("city")
    district = request.args.get("district")
    commune = request.args.get("commune")
    if not (city and district and commune):
        return jsonify({"error": "city, district, commune are required"}), 400

    try:
        rows = predict_next24h(city, district, commune)
    except Exception:
        # fallback
        rows = _simulate_forecast(city, district, commune)
        csv_path = os.path.join(FORECAST_DIR, f"{city}_{district}_{commune}.csv")
        pd.DataFrame(rows).to_csv(csv_path, index=False)

    # Tính thống kê phục vụ recommend
    temps = [r["temp"] for r in rows]
    hums = [r["humidity"] for r in rows]
    winds = [r["wind_speed"] for r in rows]
    rains = [r["rainfall"] for r in rows]

    out = {
        "city": city,
        "district": district,
        "commune": commune,
        "forecast": rows,
        "features": {
            "avg_temp_24h": round(sum(temps)/len(temps), 2) if temps else None,
            "avg_humidity_24h": round(sum(hums)/len(hums), 2) if hums else None,
            "rain_forecast_sum": round(sum(rains), 2),
            "wind_avg": round(sum(winds)/len(winds), 2) if winds else None,
        }
    }
    return jsonify(out)


# ----- Consolidated API for frontend/src (single port) -----
@app.route('/api/weather')
def api_weather():
    # Basic current weather synthesized from forecast (same-origin demo)
    city = request.args.get('city') or 'Hà Nội'
    district = request.args.get('district') or 'District 1'
    commune = request.args.get('commune') or 'Commune 1'
    try:
        rows = predict_next24h(city, district, commune)
    except Exception:
        rows = _simulate_forecast(city, district, commune)
    now = rows[0] if rows else {}
    out = {
        "name": city,
        "coord": {"lat": None, "lon": None},
        "main": {"temp": now.get("temp"), "feels_like": now.get("temp"), "humidity": now.get("humidity")},
        "weather": [{"description": "Clouds"}],
    }
    return jsonify(out)


@app.route('/api/forecast')
def api_forecast():
    city = request.args.get('city') or 'Hà Nội'
    hours = int(request.args.get('hours', 5))
    try:
        rows = predict_next24h(city, 'District 1', 'Commune 1')
    except Exception:
        rows = _simulate_forecast(city, 'District 1', 'Commune 1')
    out = {
        "city": city,
        "forecast": [{"after_hours": i+1, "temperature": r.get("temp"), "humidity": r.get("humidity")} for i, r in enumerate(rows[:hours])]
    }
    return jsonify(out)


@app.route('/api/forecast3')
def api_forecast3():
    city = request.args.get('city') or 'Hà Nội'
    try:
        rows = predict_next24h(city, 'District 1', 'Commune 1')
    except Exception:
        rows = _simulate_forecast(city, 'District 1', 'Commune 1')
    # repeat last 24h chunk to compose 72h if needed
    base = [r.get('temp') for r in rows[:24]]
    if not base:
        base = []
    temps = (base * 3)[:72]
    day_avgs = []
    for d in range(3):
        chunk = temps[d*24:(d+1)*24]
        avg = round(sum([x for x in chunk if x is not None]) / len([x for x in chunk if x is not None]), 1) if chunk else None
        day_avgs.append(avg)
    # fill forward if missing
    for i in range(3):
        if day_avgs[i] is None:
            day_avgs[i] = day_avgs[i-1] if i>0 else None
    return jsonify({"city": city, "predictions": [{"day": i+1, "avg_temp": v} for i, v in enumerate(day_avgs)]})


@app.route('/api/history')
def api_history():
    return history()


@app.route('/health')
def health():
    # basic health + env readiness
    weather_key = os.getenv('WEATHERAPI_KEY')
    status = {
        'weatherapi': 'ok' if weather_key else 'missing_key',
        'model': 'present' if os.path.exists(os.path.join(MODELS_DIR, 'lstm_weather.pt')) else 'missing',
        'version': '1.0',
    }
    return jsonify(status)


def _rule_based_irrigation(feats: dict):
    rain_sum = feats.get("rain_forecast_sum") or 0
    avg_temp = feats.get("avg_temp_24h") or 0
    avg_hum = feats.get("avg_humidity_24h") or 0
    if rain_sum > 2:
        return "Hoãn tưới", 0
    if avg_temp > 33 and avg_hum < 60:
        return "Tưới ngay", 300
    if 60 <= avg_hum <= 75:
        return "Tưới nhẹ", 200
    return "Theo dõi", 0


def _fertilizer_reco(avg_temp: float, rain_sum: float, soil_type: str, growth_stage: str):
    if 20 <= avg_temp <= 30 and rain_sum == 0 and soil_type == "trung tính":
        return "NPK 10-10-10", "150 kg/ha"
    if growth_stage in ("sinh trưởng mạnh", "phát triển mạnh"):
        return "NPK 16-8-8", "180 kg/ha"
    if avg_temp and avg_temp < 20:
        return "NPK 10-10-10", "100 kg/ha"
    return "NPK 12-12-17", "160 kg/ha"


@app.route("/recommend")
def recommend():
    city = request.args.get("city")
    district = request.args.get("district")
    commune = request.args.get("commune")
    crop = request.args.get("crop")
    if not (city and district and commune):
        return jsonify({"error": "city, district, commune are required"}), 400

    # Tính feature từ dự báo (gọi trực tiếp predict_next24h để tránh phụ thuộc context Flask)
    try:
        rows = predict_next24h(city, district, commune)
    except Exception:
        rows = _simulate_forecast(city, district, commune)
    temps = [r["temp"] for r in rows]
    hums = [r["humidity"] for r in rows]
    winds = [r["wind_speed"] for r in rows]
    rains = [r["rainfall"] for r in rows]
    feats = {
        "avg_temp_24h": round(sum(temps)/len(temps), 2) if temps else None,
        "avg_humidity_24h": round(sum(hums)/len(hums), 2) if hums else None,
        "rain_forecast_sum": round(sum(rains), 2),
        "wind_avg": round(sum(winds)/len(winds), 2) if winds else None,
    }

    # Mongo: lấy profile cây & vị trí
    locations = db.get_collection("locations")
    crop_profiles = db.get_collection("crop_profiles")
    loc = locations.find_one({"city": city, "district": district, "commune": commune})
    profile = crop_profiles.find_one({"crop": crop}) if crop else None

    # Thử dùng model tưới, nếu không có thì fallback rule
    model = load_irrigation_model()
    if model:
        action, water_ml = predict_irrigation_action(model, feats)
    else:
        action, water_ml = _rule_based_irrigation(feats)

    soil = (profile or {}).get("soil_type") or (loc or {}).get("soil_type") or "trung tính"
    stage = (profile or {}).get("growth_stage") or "bình thường"
    fert_type, fert_amount = _fertilizer_reco(feats.get("avg_temp_24h", 0), feats.get("rain_forecast_sum", 0), soil, stage)

    pesticide_warning = None
    if feats.get("avg_humidity_24h", 0) > 85 and feats.get("rain_forecast_sum", 0) > 5:
        pesticide_warning = "Ẩm cao, mưa kéo dài → cảnh báo nấm bệnh (gợi ý Ridomil Gold/Copper oxychloride)."
    if feats.get("wind_avg", 0) > 15:
        pesticide_warning = (pesticide_warning + " " if pesticide_warning else "") + "Gió mạnh > 15 km/h → hoãn phun lá."

    out = {
        "city": city,
        "district": district,
        "commune": commune,
        "crop": crop,
        "weather_forecast": {
            "temp_avg": feats.get("avg_temp_24h"),
            "humidity_avg": feats.get("avg_humidity_24h"),
            "rain_mm": feats.get("rain_forecast_sum"),
            "wind_avg": feats.get("wind_avg"),
        },
        "recommendations": {
            "irrigation": action,
            "water_ml_per_m2": water_ml,
            "fertilizer": f"{fert_type}, {fert_amount}",
            "pesticide_warning": pesticide_warning,
        }
    }
    # Lưu lịch sử
    try:
        db.get_collection("history_recommendations").insert_one({
            **out,
            "created_at": datetime.now()
        })
    except Exception:
        pass
    return jsonify(out)


@app.route("/history")
def history():
    try:
        limit = int(request.args.get('limit', 50))
    except Exception:
        limit = 50
    cur = db.get_collection("history_recommendations").find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    return jsonify(list(cur))


def _fold_ascii(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(c)).lower().strip()


def _alias_of(city: str) -> str:
    try:
        with open(VN_LOC_PATH, 'r', encoding='utf-8') as f:
            items = json.load(f)
        token = _fold_ascii(city)
        for it in items:
            name_norm = _fold_ascii(it.get('name'))
            alias_norm = _fold_ascii(it.get('alias'))
            if token == name_norm or token == alias_norm:
                return alias_norm or name_norm
    except Exception:
        pass
    return _fold_ascii(city)


@app.route('/metrics')
def metrics():
    city = request.args.get('city', '')
    alias = _alias_of(city) if city else ''
    # per-city first, then global fallback
    paths = []
    if alias:
        paths.append(os.path.join(PER_CITY_DIR, f'metrics_{alias}.txt'))
    paths.append(os.path.join(REPORTS_DIR, 'metrics.txt'))

    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    content = f.read()
                # parse simple key=value lines if possible
                data = {}
                for line in content.splitlines():
                    if '=' in line:
                        k, v = line.split('=', 1)
                        data[k.strip()] = v.strip()
                return jsonify({'path': p, 'raw': content, 'parsed': data})
            except Exception:
                break
    return jsonify({'error': 'metrics not found'}), 404


@app.route('/classification')
def classification_report_api():
    city = request.args.get('city', '')
    alias = _alias_of(city) if city else ''
    paths = []
    if alias:
        paths.append(os.path.join(PER_CITY_DIR, f'classification_{alias}.txt'))
    paths.append(os.path.join(REPORTS_DIR, 'classification.txt'))

    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    content = f.read()
                return jsonify({'path': p, 'report': content})
            except Exception:
                break
    return jsonify({'error': 'classification report not found'}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
