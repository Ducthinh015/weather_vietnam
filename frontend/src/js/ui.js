import { getWeather, getForecast, getForecast3, getHistory } from './api.js';
import { renderLineChart, renderMultiLineChart } from './chart.js';

async function handleWeatherForm(e){
  e.preventDefault();
  const city = e.target.city.value.trim();
  const out = document.querySelector('#weatherResult');
  const err = document.querySelector('#error');
  const card = document.getElementById('weatherSummary');
  const elCity = document.getElementById('wsCity');
  const elCoord = document.getElementById('wsCoord');
  const elTemp = document.getElementById('wsTemp');
  const elFeels = document.getElementById('wsFeels');
  const elHum = document.getElementById('wsHumidity');
  const elCond = document.getElementById('wsCond');
  if (err) err.textContent = '';
  
  if (out) { out.classList.remove('d-none'); out.textContent = 'Loading...'; }
  if (card) card.classList.add('d-none');
  try{
    const data = await getWeather(city);
    
    if (out) out.textContent = JSON.stringify(data, null, 2);
    
    const name = data?.name || city;
    const lat = data?.coord?.lat;
    const lon = data?.coord?.lon;
    const temp = data?.main?.temp;
    const feels = data?.main?.feels_like;
    const hum = data?.main?.humidity;
    const cond = Array.isArray(data?.weather) && data.weather[0]?.description ? data.weather[0].description : '';
    if (elCity) elCity.textContent = name || '—';
    if (elCoord) elCoord.textContent = (lat!=null && lon!=null) ? `(${lat}, ${lon})` : '—';
    if (elTemp) elTemp.textContent = (temp!=null) ? `${temp} °C` : '—';
    if (elFeels) elFeels.textContent = (feels!=null) ? `${feels} °C` : '—';
    if (elHum) elHum.textContent = (hum!=null) ? `${hum} %` : '—';
    if (elCond) elCond.textContent = cond || '—';
    if (card) card.classList.remove('d-none');
  }catch(ex){
    if (out) out.textContent = '';
    if (card) card.classList.add('d-none');
    const msg = (ex && ex.message) ? ex.message : String(ex);
    if (err) err.textContent = msg; else console.error(msg);
  }
}

async function runForecast(city){
  const out = document.querySelector('#forecastResult');
  const err = document.querySelector('#error');
  if (err) err.textContent='';
  if (out) out.textContent = 'Loading...';
  try{
    const [current, data] = await Promise.all([
      getWeather(city),
      getForecast(city, 5)
    ]);
    if (out) out.textContent = JSON.stringify(data, null, 2);
    const isAlt = data.forecast && data.forecast.length && (data.forecast[0].temp_c !== undefined);
    const labels = ['Hiện tại', ...data.forecast.map((x,i)=> isAlt ? (x.time?.includes(':')? x.time : `+${i+1}h`) : `+${x.after_hours}h`)];
    const temps = data.forecast.map((x,i)=> isAlt ? x.temp_c : x.temperature);
    const hums = data.forecast.map((x,i)=> x.humidity);
    const currentTemp = current?.main?.temp;
    const tempDatasets = [
      { label: 'Hiện tại (°C)', data: [currentTemp, ...Array(temps.length).fill(null)], borderColor: '#ef4444', backgroundColor: '#ef444411', pointRadius: 4, tension: 0.2 },
      { label: 'Dự báo (°C)', data: [null, ...temps], borderColor: '#60a5fa', backgroundColor: '#60a5fa22', tension: 0.2, fill: true }
    ];
    renderMultiLineChart(document.getElementById('tChart'), labels, tempDatasets);
    renderLineChart(document.getElementById('hChart'), data.forecast.map((x,i)=> isAlt ? (x.time?.includes(':')? x.time : `+${i+1}h`) : `+${x.after_hours}h`), hums, 'Độ ẩm (%)');
  }catch(ex){
    if (out) out.textContent = '';
    const msg = (ex && ex.message) ? ex.message : String(ex);
    if (err) err.textContent = msg; else if (out) out.textContent = msg;
  }
}

async function handleForecastForm(e){
  e.preventDefault();
  const city = e.target.city.value.trim();
  await runForecast(city);
}

async function handleForecast3Form(e){
  e.preventDefault();
  const city = e.target.city.value.trim();
  const info = document.querySelector('#forecast3Text');
  const ctx = document.getElementById('arimaChart');
  info.classList.add('d-none');
  info.textContent = '';
  try{
    const data = await getForecast3(city);
    const labels = ['Ngày 1','Ngày 2','Ngày 3'];
    const ds = [{ label: 'Nhiệt độ trung bình (°C)', data: data.predictions.map(p=>p.avg_temp),
      borderColor: '#0ea5e9', backgroundColor: '#d7d2c411', tension: 0.2, fill: true }];
    renderMultiLineChart(ctx, labels, ds);
    info.textContent = `Dự báo: Ngày 1: ${data.predictions[0].avg_temp}°C • Ngày 2: ${data.predictions[1].avg_temp}°C • Ngày 3: ${data.predictions[2].avg_temp}°C`;
    info.classList.remove('d-none');
  }catch(ex){
    info.textContent = ex.message;
    info.classList.remove('d-none');
    info.classList.replace('alert-info', 'alert-danger');
  }
}

async function handleHistoryForm(e){
  e.preventDefault();
  const city = e.target.city.value.trim();
  const tbody = document.querySelector('#historyTableBody');
  const ctx = document.getElementById('historyChart');
  tbody.innerHTML = '<tr><td colspan="3">Đang tải...</td></tr>';
  try{
    const rows = await getHistory(city, 100);
    tbody.innerHTML = '';
    rows.forEach(r=>{
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${new Date(r.timestamp).toLocaleString()}</td><td>${r.city}</td><td>${r.prediction?.toFixed(1)}</td>`;
      tbody.appendChild(tr);
    });
    const labels = rows.slice().reverse().map(r=> new Date(r.timestamp).toLocaleDateString());
    const ds = [{ label: 'Dự báo (°C)', data: rows.slice().reverse().map(r=> r.prediction), borderColor: '#22c55e', backgroundColor: '#22c55e11', tension: 0.2, fill: true }];
    renderMultiLineChart(ctx, labels, ds);
  }catch(ex){
    tbody.innerHTML = `<tr><td colspan="3" class="text-danger">${ex.message}</td></tr>`;
  }
}

async function handleIrrigationForm(e){
  e.preventDefault();
  const city = e.target.city.value.trim();
  await renderIrrigation(city);
}

async function renderIrrigation(city){
  const box = document.getElementById('irrResult');
  const reason = document.getElementById('irrReason');
  if (!box || !reason) return;
  box.className = 'alert alert-info';
  box.classList.remove('d-none');
  box.textContent = 'Đang tính gợi ý...';
  reason.textContent = '';
  try{
    const data = await getForecast(city, 5);
    const series = data?.forecast || [];
    const next3 = series.slice(0,3);
    const next5 = series.slice(0,5);
    const hum3min = Math.min(...next3.map(x=> Number(x.humidity ?? 100)));
    const hum5max = Math.max(...next5.map(x=> Number(x.humidity ?? 0)));
    const temp3max = Math.max(...next3.map(x=> Number((x.temp_c ?? x.temperature) ?? -99)));

    if (Number.isFinite(hum5max) && hum5max >= 75){
      box.className = 'alert alert-danger';
      box.innerHTML = 'Kết luận: <strong>HOÃN TƯỚI</strong>. Độ ẩm dự báo ≥ 75% trong 3–5 giờ tới.';
      reason.textContent = `Lý do: Độ ẩm tối đa 5 giờ tới đạt ${hum5max}% (cao).`;
      return;
    }
    if (Number.isFinite(temp3max) && Number.isFinite(hum3min) && temp3max > 32 && hum3min < 55){
      box.className = 'alert alert-success';
      box.innerHTML = 'Kết luận: <strong>TƯỚI NGAY</strong>. Nhiệt độ > 32°C và độ ẩm < 55% trong 3 giờ tới.';
      reason.textContent = `Lý do: Nhiệt độ tối đa 3 giờ tới ${temp3max}°C, độ ẩm tối thiểu ${hum3min}%.`;
      return;
    }
    box.className = 'alert alert-warning';
    box.innerHTML = 'Kết luận: <strong>TƯỚI NHẸ</strong> 8–12 l/m².';
    reason.textContent = 'Lý do: Không có mưa/ẩm cao và không quá nóng trong vài giờ tới.';
  }catch(ex){
    box.className = 'alert alert-danger';
    box.textContent = ex.message || String(ex);
    reason.textContent = '';
  }
}

window.addEventListener('DOMContentLoaded', ()=>{
  const wf = document.querySelector('#weatherForm');
  const ff = document.querySelector('#forecastForm');
  const f3 = document.querySelector('#forecast3Form');
  const hf = document.querySelector('#historyForm');
  const irf = document.querySelector('#irrigationForm');
  const btnF = document.getElementById('btnForecast');
  const btnIrrShort = document.getElementById('btnIrrigationShort');
  const btnIrr3 = document.getElementById('btnIrrigation3');
  if(wf) wf.addEventListener('submit', handleWeatherForm);
  if(ff) ff.addEventListener('submit', handleForecastForm);
  if(f3) f3.addEventListener('submit', handleForecast3Form);
  if(hf) hf.addEventListener('submit', handleHistoryForm);
  if(irf) irf.addEventListener('submit', handleIrrigationForm);
  if(btnF && ff){
    btnF.addEventListener('click', ()=>{
      const city = (ff.city && ff.city.value ? ff.city.value.trim() : '').toString();
      if(city){ runForecast(city); }
    });
  }
  
  if (ff && ff.city && btnIrrShort){
    const sync = ()=>{ btnIrrShort.disabled = !(ff.city.value && ff.city.value.trim()); };
    ff.city.addEventListener('input', sync); sync();
    btnIrrShort.addEventListener('click', ()=>{
      const city = ff.city.value.trim();
      if(!city) return; 
      location.href = `./irrigation.html?city=${encodeURIComponent(city)}`;
    });
  }
  if (f3 && f3.city && btnIrr3){
    const sync3 = ()=>{ btnIrr3.disabled = !(f3.city.value && f3.city.value.trim()); };
    f3.city.addEventListener('input', sync3); sync3();
    btnIrr3.addEventListener('click', ()=>{
      const city = f3.city.value.trim();
      if(!city) return;
      location.href = `./irrigation.html?city=${encodeURIComponent(city)}`;
    });
  }

  
  try{
    const params = new URLSearchParams(location.search);
    const cityParam = params.get('city');
    if(cityParam){
      if (ff) { ff.city.value = cityParam; runForecast(cityParam); }
      else if (wf) { wf.city.value = cityParam; handleWeatherForm(new Event('submit', {bubbles:true, cancelable:true})); }
      const irf2 = document.querySelector('#irrigationForm');
      if (irf2){ irf2.city.value = cityParam; handleIrrigationForm(new Event('submit', {bubbles:true, cancelable:true})); }
      else { renderIrrigation(cityParam); }
    }
    
    const tj = document.getElementById('toggleJson');
    const pre = document.getElementById('forecastResult');
    if (tj && pre){
      tj.addEventListener('click', ()=>{
        const hidden = pre.classList.toggle('d-none');
        tj.textContent = hidden ? 'Hiển thị JSON' : 'Ẩn JSON';
      });
    }
    const th = document.getElementById('toggleHomeJson');
    const preHome = document.getElementById('weatherResult');
    if (th && preHome){
      th.addEventListener('click', ()=>{
        const hidden = preHome.classList.toggle('d-none');
        th.textContent = hidden ? 'Hiển thị JSON' : 'Ẩn JSON';
      });
    }
  }catch(e){}
});

