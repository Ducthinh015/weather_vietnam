const API_BASE = (window.API_BASE) || "http://localhost:5000/api";

export async function getWeather(city){
  const url = `${API_BASE}/weather?city=${encodeURIComponent(city)}&t=${Date.now()}`;
  const res = await fetch(url, { cache: 'no-store' });
  if(!res.ok) throw new Error(`Weather API error: ${res.status}`);
  return res.json();
}

export async function getForecast(city, hours=5){
  const url = `${API_BASE}/forecast?city=${encodeURIComponent(city)}&hours=${hours}&t=${Date.now()}`;
  const res = await fetch(url, { cache: 'no-store' });
  if(!res.ok) throw new Error(`Forecast API error: ${res.status}`);
  return res.json();
}
