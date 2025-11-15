const API_BASE = (window.API_BASE) || "http://localhost:5000/api";

export async function getWeather(city){
  const res = await fetch(`${API_BASE}/weather?city=${encodeURIComponent(city)}`);
  if(!res.ok) throw new Error(`Lỗi Weather API: ${res.status}`);
  return res.json();
}

export async function getForecast(city, hours=5){
  const res = await fetch(`${API_BASE}/forecast?city=${encodeURIComponent(city)}&hours=${hours}`);
  if(!res.ok) throw new Error(`Lỗi Forecast API: ${res.status}`);
  return res.json();
}
