import { API_BASE } from './config.js';
import { loadCities as fetchCities } from './api.js';

function $(s){ return document.querySelector(s); }
function el(tag, attrs={}, ...children){
  const e = document.createElement(tag);
  Object.entries(attrs).forEach(([k,v])=>{
    if(k==='class') e.className = v; else if(k==='html') e.innerHTML=v; else e.setAttribute(k,v);
  });
  children.forEach(c=> e.appendChild(typeof c==='string'? document.createTextNode(c): c));
  return e;
}

async function populateCityList(){
  try{
    const cities = await fetchCities();
    const dl = $('#cityList');
    if(dl){
      dl.innerHTML = '';
      cities.forEach(name=>{
        const opt = el('option', { value: typeof name==='string'? name : (name?.name||'') });
        if(opt.getAttribute('value')) dl.appendChild(opt);
      });
    }
  }catch(_){ /* ignore */ }
}

async function fetchHistory(city, limit){
  const url = `${API_BASE}/weather/history?city=${encodeURIComponent(city)}&limit=${limit}`;
  const res = await fetch(url);
  if(!res.ok) throw new Error(`Lỗi history API: ${res.status}`);
  return res.json();
}

let chart;
async function renderChart(items){
  const ctx = $('#histChart').getContext('2d');
  const labels = items.map(r=> r.timestamp);
  const temp = items.map(r=> r.temp ?? r.main?.temp ?? null);
  const hum = items.map(r=> r.humidity ?? r.main?.humidity ?? null);
  const rain = items.map(r=> r.rain_mm ?? r.rain?.['1h'] ?? 0);
  if(chart){ chart.destroy(); }
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label:'Nhiệt độ (°C)', data: temp, borderColor:'#ef4444', tension:.2, yAxisID:'y1' },
        { label:'Độ ẩm (%)', data: hum, borderColor:'#3b82f6', tension:.2, yAxisID:'y2' },
        { label:'Mưa (mm)', data: rain, borderColor:'#10b981', tension:.2, yAxisID:'y3' },
      ]
    },
    options: {
      responsive: true,
      interaction: { mode:'index', intersect:false },
      scales: {
        y1: { type:'linear', position:'left', title:{ display:true, text:'°C' } },
        y2: { type:'linear', position:'right', title:{ display:true, text:'%' }, grid:{ drawOnChartArea:false } },
        y3: { type:'linear', position:'right', title:{ display:true, text:'mm' }, grid:{ drawOnChartArea:false } },
      }
    }
  });
}

function renderTable(items){
  const tbody = $('#histTable tbody');
  tbody.innerHTML = '';
  for(const r of items){
    const tr = el('tr', {},
      el('td', {}, r.timestamp || ''),
      el('td', {}, String(r.temp ?? r.main?.temp ?? '')),
      el('td', {}, String(r.humidity ?? r.main?.humidity ?? '')),
      el('td', {}, String(r.rain_mm ?? r.rain?.['1h'] ?? 0)),
    );
    tbody.appendChild(tr);
  }
}

async function onSubmit(e){
  e.preventDefault();
  const fd = new FormData(e.target);
  const city = (fd.get('city')||'').trim();
  const limit = parseInt(fd.get('limit')||'100',10);
  if(!city) return;
  const data = await fetchHistory(city, limit);
  const items = data?.data?.items || [];
  await renderChart(items);
  renderTable(items);
}

export function initHistoryPage(){
  populateCityList();
  const form = document.getElementById('historyForm');
  if(form) form.addEventListener('submit', onSubmit);
}
