import { API_BASE, weatherEndpoint } from "./config.js";

async function request(url, options = {}) {
  const res = await fetch(url, options);
  let payload = null;
  try {
    payload = await res.json();
  } catch (_) {
    payload = null;
  }

  if (!res.ok || payload?.status === "error") {
    const message = payload?.error?.message || payload?.message || `Request failed: ${res.status}`;
    throw new Error(message);
  }

  return payload?.data ?? payload ?? {};
}

export async function loadCities() {
  const data = await request(`${weatherEndpoint}/cities`);
  return data?.cities ?? data ?? [];
}

export async function loadDashboard(city) {
  const query = city ? `?city=${encodeURIComponent(city)}` : "";
  return request(`${weatherEndpoint}/dashboard${query}`);
}

export async function getWeather(city) {
  return request(`${API_BASE}/weather?city=${encodeURIComponent(city)}`);
}

export async function getRealtime(city) {
  return request(`${API_BASE}/weather/realtime?city=${encodeURIComponent(city)}`);
}

export async function getForecast(city, hours = 6) {
  return request(`${API_BASE}/weather/predict?city=${encodeURIComponent(city)}&steps=${hours}`);
}

export { getForecast as getForecasts };

export async function predict(city, steps = 6) {
  return request(`${API_BASE}/weather/predict?city=${encodeURIComponent(city)}&steps=${steps}`);
}

export async function triggerFetchNow() {
  return request(`${weatherEndpoint}/fetch-now`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
}

export async function triggerTrainNow() {
  return request(`${weatherEndpoint}/train-now`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
}

export async function getCities() {
  // Backward compatibility helper for older modules expecting the old signature.
  return { data: { cities: await loadCities() } };
}

export async function getForecast3() {
  return { predictions: [], crop_groups: [] };
}

export async function getHistory() {
  return [];
}
