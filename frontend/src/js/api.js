const API_BASE = window.API_BASE || "http://localhost:5000/api";

export async function getWeather(city){
  const url = `${API_BASE}/weather?city=${encodeURIComponent(city)}&t=${Date.now()}`;
  const res = await fetch(url, { cache: 'no-store' });
  if(!res.ok){
    const text = await res.text().catch(()=> '');
    throw new Error(`Weather API error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function getForecast(city, hours=5){
  const url = `${API_BASE}/forecast?city=${encodeURIComponent(city)}&hours=${hours}&t=${Date.now()}`;
  const res = await fetch(url, { cache: 'no-store' });
  if(!res.ok){
    const text = await res.text().catch(()=> '');
    throw new Error(`Forecast API error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function getForecast3(city){
  const url = `${API_BASE}/forecast3?city=${encodeURIComponent(city)}&t=${Date.now()}`;
  const res = await fetch(url, { cache: 'no-store' });
  if(!res.ok){
    const text = await res.text().catch(()=> '');
    throw new Error(`Forecast3 API error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function getHistory(city='', limit=50){
  const url = `${API_BASE}/history?city=${encodeURIComponent(city)}&limit=${limit}&t=${Date.now()}`;
  const res = await fetch(url, { cache: 'no-store' });
  if(!res.ok){
    const text = await res.text().catch(()=> '');
    throw new Error(`History API error ${res.status}: ${text}`);
  }
  return res.json();
}
