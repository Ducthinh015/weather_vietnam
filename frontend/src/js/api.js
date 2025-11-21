const API_BASE =
  (window.API_BASE) ||
  "http://localhost:8000/api";

// Legacy-style helpers (kept for compatibility if some pages import them)
export async function getWeather(city) {
  const res = await fetch(
    `${API_BASE}/weather?city=${encodeURIComponent(city)}`
  );
  if (!res.ok) throw new Error(`Lỗi Weather API: ${res.status}`);
  return res.json();
}

export async function getForecast(city, hours = 5) {
  // Map to new predict API: hours≈steps
  const res = await fetch(
    `${API_BASE}/weather/predict?city=${encodeURIComponent(city)}&steps=${hours}`
  );
  if (!res.ok) throw new Error(`Lỗi Forecast API: ${res.status}`);
  return res.json();
}

// Backward-compatible alias (some pages may import { getForecasts })
export { getForecast as getForecasts };

// New helpers aligned with multi-city backend
export async function getCities() {
  const res = await fetch(`${API_BASE}/weather/cities`);
  if (!res.ok) throw new Error(`Lỗi Cities API: ${res.status}`);
  return res.json();
}

export async function getRealtime(city) {
  const res = await fetch(
    `${API_BASE}/weather/realtime?city=${encodeURIComponent(city)}`
  );
  if (!res.ok) throw new Error(`Lỗi Realtime API: ${res.status}`);
  return res.json();
}

export async function predict(city, steps = 6) {
  const res = await fetch(
    `${API_BASE}/weather/predict?city=${encodeURIComponent(city)}&steps=${steps}`
  );
  if (!res.ok) throw new Error(`Lỗi Predict API: ${res.status}`);
  return res.json();
}

export async function fetchNow() {
  const res = await fetch(`${API_BASE}/weather/fetch-now`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`Lỗi Fetch-Now API: ${res.status}`);
  return res.json();
}

export async function trainNow() {
  const res = await fetch(`${API_BASE}/weather/train-now`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`Lỗi Train-Now API: ${res.status}`);
  return res.json();
}

// Compatibility helpers expected by older UI modules
export async function getForecast3(city) {
  // If you later expose a dedicated 3-day endpoint, swap this implementation.
  // For now, return an empty structure so UI can degrade gracefully.
  return { predictions: [], crop_groups: [] };
}

export async function getHistory(city, limit = 100) {
  // No history endpoint yet; return empty list for compatibility.
  return [];
}
