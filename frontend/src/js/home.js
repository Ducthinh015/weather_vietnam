import { getWeather, getRealtime, loadCities as fetchCities } from './api.js';

function $(sel){ return document.querySelector(sel); }

let CITIES = [];
let CITY_SET = new Set();

async function populateCities(){
  try{
    const cities = await fetchCities();
    CITIES = cities;
    CITY_SET = new Set(cities.map(c => (typeof c === 'string' ? c : c?.name || c)));
    const dl = document.getElementById('cityList');
    if(dl){
      dl.innerHTML = '';
      CITIES.forEach(name => {
        const opt = document.createElement('option');
        opt.value = typeof name === 'string' ? name : (name?.name || '');
        if(opt.value) dl.appendChild(opt);
      });
    }
  }catch(_){ /* bỏ qua, người dùng có thể nhập tay */ }
}

async function onSubmit(e){
  e.preventDefault();
  const city = (new FormData(e.target).get('city') || '').trim();
  const err = $('#error');
  const out = $('#weatherResult');
  err.textContent = '';
  if(out) out.textContent = '';
  if(!city){ err.textContent = 'Vui lòng nhập tên tỉnh/thành'; return; }
  if(CITY_SET.size && !CITY_SET.has(city)){
    err.textContent = 'Tên tỉnh/thành không hợp lệ. Vui lòng chọn từ danh sách.';
    return;
  }
  try{
    // Ưu tiên realtime từ Mongo; nếu chưa có dữ liệu thì fallback qua direct Weather API
    let resp;
    try {
      resp = await getRealtime(city);
    } catch (ex) {
      resp = await getWeather(city);
    }

    // Chuẩn hóa shape
    const payload = resp?.data || resp;
    const w = payload?.realtime || payload?.weather || {};
    const main = w.main || {};
    const wind = w.wind || {};

    // Support both flat (realtime) and nested (direct API) shapes
    const temp = (w.temp ?? main.temp);
    const humidity = (w.humidity ?? main.humidity);
    const pressure = (w.pressure ?? main.pressure);
    const windSpeed = (w.wind_speed ?? wind.speed);
    const clouds = (w.cloud ?? (w.clouds && (w.clouds.all ?? w.clouds)));
    const rain = (w.rain_mm ?? (w.rain && (w.rain['1h'] ?? w.rain)));
    const icon = Array.isArray(w.weather) && w.weather[0]?.icon ? w.weather[0].icon : null;
    const condRaw = Array.isArray(w.weather) ? (w.weather[0]?.description || w.weather[0]?.text) : (w.condition || '--');
    const cond = translateCondition(condRaw);
    const tsRaw = w.timestamp || w.timestamp_utc || payload?.timestamp || payload?.realtime?.timestamp || '--';
    const ts = formatVietTime(tsRaw);

    // Helpers
    const set = (id, val)=>{ const el = document.getElementById(id); if(el) el.textContent = (val ?? '--'); };
    const fmt = (v, d=1)=> (typeof v === 'number' ? v.toFixed(d) : (v ?? '--'));

    // Render KPIs
    set('kpi-temp', fmt(temp));
    set('kpi-humidity', humidity != null ? fmt(humidity, 0) : '--');
    set('kpi-pressure', pressure != null ? fmt(pressure, 0) : '--');
    set('kpi-wind', windSpeed != null ? fmt(windSpeed, 1) : '--');
    set('kpi-condition', cond);
    const iconEl = document.getElementById('kpi-icon');
    if(iconEl){ iconEl.src = icon ? (icon.startsWith('http') ? icon : `https:${icon}`) : ''; iconEl.style.display = icon ? 'inline-block' : 'none'; }
    set('kpi-time', ts);

    // Hiển thị full JSON (debug) ở dưới nếu tồn tại phần tử
    if(out) out.textContent = JSON.stringify(resp, null, 2);
  }catch(ex){
    err.textContent = typeof ex?.message === 'string' ? ex.message : 'Lỗi không xác định';
  }
}

export function initHomePage(){
  populateCities();
  const form = document.getElementById('weatherForm');
  if(form){ form.addEventListener('submit', onSubmit); }
}

// ---------------- helpers ----------------
function translateCondition(en){
  if(!en || typeof en !== 'string') return '--';
  const s = en.toLowerCase();
  const map = [
    [/sunny|clear/, 'Trời quang mây'],
    [/partly\s*cloudy|patchy\s*cloud|intermittent\s*clouds/, 'Ít mây'],
    [/cloudy|overcast/, 'Nhiều mây'],
    [/light\s*rain|drizzle|patchy\s*rain/, 'Mưa nhẹ'],
    [/rain|showers/, 'Mưa'],
    [/thunder|storm/, 'Dông bão'],
    [/mist|fog/, 'Sương mù'],
    [/snow|sleet|hail/, 'Tuyết/Mưa đá'],
  ];
  for(const [re, vi] of map){ if(re.test(s)) return vi; }
  return en; // fallback giữ nguyên
}

function formatVietTime(ts){
  if(!ts) return '--';
  try{
    const d = new Date(ts);
    if(isNaN(d.getTime())) return ts;
    return new Intl.DateTimeFormat('vi-VN', {
      timeZone: 'Asia/Ho_Chi_Minh',
      dateStyle: 'medium',
      timeStyle: 'medium'
    }).format(d);
  }catch(_){ return ts; }
}
