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
  
  if (out) { out.classList.remove('d-none'); out.textContent = 'Đang tải...'; }
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
  if (out) out.textContent = 'Đang tải...';
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
    const params = new URLSearchParams(location.search);
    const mode = (params.get('mode') || '5h').toLowerCase();
    const h1 = document.querySelector('h1');

    if (mode === '3d'){
      if (h1) h1.textContent = 'Hướng dẫn chăm sóc nông nghiệp (3 ngày)';
      const data3 = await getForecast3(city);
      const pred = Array.isArray(data3?.predictions) ? data3.predictions : [];
      const d1 = pred[0] || {}; const d2 = pred[1] || {}; const d3 = pred[2] || {};

      const arr = [d1?.avg_temp, d2?.avg_temp, d3?.avg_temp].filter(v=> v!=null);
      const tmax = Math.max(...arr);
      const tmin = Math.min(...arr);

      let decision = { cls: 'alert alert-warning', html: 'Khuyến nghị: <strong>TƯỚI CÂN NHẮC</strong>.', why: 'Nhiệt độ trung bình 3 ngày không quá cực đoan.' };
      if (Number.isFinite(tmax) && tmax >= 34){
        decision = { cls: 'alert alert-success', html: 'Khuyến nghị: <strong>TƯỚI NGAY</strong>.', why: `Có ngày nóng (≥34°C).` };
      }

      // Client-side crop rules (aligned with backend)
      const cropRules = {
        'luong thuc': {hot: 33, humid: 78, water_mm: 10, label: 'Lương thực (lúa, mì, sắn,...)'},
        'cay an qua': {hot: 32, humid: 75, water_mm: 8, label: 'Cây ăn quả'},
        'cay cong nghiep': {hot: 32, humid: 75, water_mm: 7, label: 'Cây công nghiệp'},
        'rau cu qua': {hot: 31, humid: 75, water_mm: 6, label: 'Rau củ quả'}
      };
      const allKeys = Object.keys(cropRules);
      const allowed = Array.isArray(data3?.crop_groups) && data3.crop_groups.length ? data3.crop_groups.map(s=> s.toLowerCase()) : allKeys;
      const cropKeys = allKeys.filter(k=> allowed.includes(k));
      const vAction = (a)=> a==='postpone'?'Hoãn tưới':(a==='irrigate_now'?'Tưới ngay':'Tưới nhẹ');
      const advise = (d, rule)=>{
        if (d.avg_humidity != null && d.avg_humidity >= rule.humid) return {action:'postpone', water_mm:0, reason:`Độ ẩm TB ≥ ${rule.humid}%`};
        if (d.max_temp != null && d.max_temp >= rule.hot && (d.avg_humidity!=null && d.avg_humidity<=60)) return {action:'irrigate_now', water_mm:rule.water_mm, reason:`Nắng nóng (≥${rule.hot}°C) & ẩm thấp`};
        return {action:'light_irrigation', water_mm: Math.max(4, rule.water_mm-2), reason:'Điều kiện trung bình'};
      };
      const allDays = [d1,d2,d3];
      const actionsRaw = [];
      const dayRows = allDays.map((d)=>{
        const cells = cropKeys.map(k=>{
          const a = advise(d, cropRules[k]);
          actionsRaw.push(a.action);
          return `<td>${vAction(a.action)}</td>`;
        }).join('');
        return `<tr><td></td><td>${d.avg_temp??'-'}</td><td>${d.avg_humidity??'-'}%</td>${cells}</tr>`;
      });
      const counts = actionsRaw.reduce((m,a)=>{ m[a]=(m[a]||0)+1; return m; },{});
      const pick = ()=>{
        const order = ['postpone','light_irrigation','irrigate_now'];
        let best = null, bestN=-1;
        for (const k of Object.keys(counts)){
          const n = counts[k];
          if (n>bestN || (n===bestN && order.indexOf(k)<order.indexOf(best))) { best=k; bestN=n; }
        }
        return best||'light_irrigation';
      };
      const globalAct = pick();
      const actMap = { postpone: {cls:'alert alert-danger', text:'HOÃN TƯỚI'}, light_irrigation:{cls:'alert alert-warning', text:'TƯỚI NHẸ'}, irrigate_now:{cls:'alert alert-success', text:'TƯỚI NGAY'} };
      decision.cls = actMap[globalAct].cls;
      decision.html = `Khuyến nghị: <strong>${actMap[globalAct].text}</strong>.`;
      const reasons = [
        `Nhiệt độ TB 3 ngày: ${allDays.map(d=> d.avg_temp??'-').join(' / ')} °C`,
        `Độ ẩm TB 3 ngày: ${allDays.map(d=> (d.avg_humidity!=null? d.avg_humidity+'%':'-')).join(' / ')}`,
        `Số lượng khuyến nghị theo nhóm cây: Hoãn tưới=${counts.postpone||0}, Tưới nhẹ=${counts.light_irrigation||0}, Tưới ngay=${counts.irrigate_now||0}`
      ];
      const cropHeader = cropKeys.map(k=>`<th>${cropRules[k].label}</th>`).join('');
      const subHeader = '';
      const thead = `<thead>
        <tr><th>Ngày</th><th>TB (°C)</th><th>Độ ẩm TB</th>${cropHeader}</tr>
        <tr><th></th><th></th><th></th>${subHeader}</tr>
      </thead>`;
      let table = `<div class=\"table-responsive\"><table class=\"table table-sm table-striped\">${thead}<tbody>`+
        dayRows.map((rowHtml, idx)=> rowHtml.replace('<td></td>', `<td>Ngày ${idx+1}</td>`)).join('')+
        '</tbody></table></div>';
      box.className = decision.cls;
      box.innerHTML = decision.html;
      const reasonsHtml = `<ul class="mb-0">${reasons.map(r=>`<li>${r}</li>`).join('')}</ul>`;
      reason.innerHTML = `${reasonsHtml}<hr class="my-3"/>${table}`;
      return;
    }

    // default: 5h short-term
    if (h1) h1.textContent = 'Hướng dẫn chăm sóc nông nghiệp (5 giờ)';
    const data5 = await getForecast(city, 5);
    const series = data5?.forecast || [];
    const next3 = series.slice(0,3);
    const next5 = series.slice(0,5);
    const hum3min = Math.min(...next3.map(x=> Number(x.humidity ?? 100)));
    const hum5max = Math.max(...next5.map(x=> Number(x.humidity ?? 0)));
    const temp3max = Math.max(...next3.map(x=> Number((x.temp_c ?? x.temperature) ?? -99)));

    let decision = { cls: 'alert alert-warning', html: 'Khuyến nghị: <strong>TƯỚI NHẸ</strong>.', why: 'Không có mưa/ẩm cao và không quá nóng trong vài giờ tới.' };
    if (Number.isFinite(hum5max) && hum5max >= 75){
      decision = { cls: 'alert alert-danger', html: 'Khuyến nghị: <strong>HOÃN TƯỚI</strong>.', why: `Độ ẩm tối đa 5 giờ tới đạt ${hum5max}%.` };
    } else if (Number.isFinite(temp3max) && Number.isFinite(hum3min) && temp3max > 32 && hum3min < 55){
      decision = { cls: 'alert alert-success', html: 'Khuyến nghị: <strong>TƯỚI NGAY</strong>.', why: `Nhiệt độ tối đa 3 giờ tới ${temp3max}°C, độ ẩm tối thiểu ${hum3min}%.` };
    }

    // Build single table with multi-crop columns
    const cropRules = {
      'luong thuc': {hot: 33, humid: 78, water_mm: 10, label: 'Lương thực (lúa, mì, sắn,...)'},
      'cay an qua': {hot: 32, humid: 75, water_mm: 8, label: 'Cây ăn quả'},
      'cay cong nghiep': {hot: 32, humid: 75, water_mm: 7, label: 'Cây công nghiệp'},
      'rau cu qua': {hot: 31, humid: 75, water_mm: 6, label: 'Rau củ quả'}
    };
    // Fetch crop_groups to filter columns
    let cropKeys = Object.keys(cropRules);
    try{
      const g = await getForecast3(city);
      const allowed = Array.isArray(g?.crop_groups) && g.crop_groups.length ? g.crop_groups.map(s=> s.toLowerCase()) : cropKeys;
      cropKeys = cropKeys.filter(k=> allowed.includes(k));
    }catch(_){ /* ignore and show all by default */ }
    const vAction = (a)=> a==='postpone'?'Hoãn tưới':(a==='irrigate_now'?'Tưới ngay':'Tưới nhẹ');
    const shortAdv = (rule)=>{
      if (Number.isFinite(hum5max) && hum5max >= rule.humid) return {action:'postpone', water_mm:0, reason:`Độ ẩm ≥ ${rule.humid}% (5h)`};
      if (Number.isFinite(temp3max) && Number.isFinite(hum3min) && temp3max >= rule.hot && hum3min <= 55) return {action:'irrigate_now', water_mm:rule.water_mm, reason:`Nóng (≥${rule.hot}°C) & ẩm thấp (≤55%)`};
      return {action:'light_irrigation', water_mm: Math.max(4, rule.water_mm-2), reason:'Điều kiện trung bình (5h)'};
    };
    const cropHeader = cropKeys.map(k=>`<th>${cropRules[k].label}</th>`).join('');
    const subHeader = '';
    const head = `<thead>
      <tr><th>Giờ</th><th>Nhiệt độ</th><th>Độ ẩm</th>${cropHeader}</tr>
    </thead>`;
    const body = next5.map((x,i)=>{
      const label = x.time && x.time.includes(':') ? x.time : `+${i+1}h`;
      const t = (x.temp_c ?? x.temperature);
      const h = x.humidity;
      const cells = cropKeys.map(k=>{ const a = shortAdv(cropRules[k]); return `<td>${vAction(a.action)}</td>`; }).join('');
      return `<tr><td>${label}</td><td>${t??'-'}°C</td><td>${h??'-'}%</td>${cells}</tr>`;
    }).join('');
    const allActions = next5.length ? cropKeys.map(k=> shortAdv(cropRules[k]).action) : [];
    const counts = allActions.reduce((m,a)=>{ m[a]=(m[a]||0)+1; return m; },{});
    const order = ['postpone','light_irrigation','irrigate_now'];
    let best='light_irrigation', bestN=-1;
    for (const k of Object.keys(counts)){
      const n=counts[k]; if (n>bestN || (n===bestN && order.indexOf(k)<order.indexOf(best))){ best=k; bestN=n; }
    }
    const actMap = { postpone: {cls:'alert alert-danger', text:'HOÃN TƯỚI'}, light_irrigation:{cls:'alert alert-warning', text:'TƯỚI NHẸ'}, irrigate_now:{cls:'alert alert-success', text:'TƯỚI NGAY'} };
    decision.cls = actMap[best].cls;
    decision.html = `Khuyến nghị: <strong>${actMap[best].text}</strong>.`;
    const reasons = [
      `Nhiệt độ tối đa 3 giờ tới: ${Number.isFinite(temp3max)? temp3max+'°C':'-'}`,
      `Độ ẩm tối đa 5 giờ tới: ${Number.isFinite(hum5max)? hum5max+'%':'-'}`,
      `Độ ẩm tối thiểu 3 giờ tới: ${Number.isFinite(hum3min)? hum3min+'%':'-'}`,
      `Số lượng khuyến nghị theo nhóm cây: Hoãn tưới=${counts.postpone||0}, Tưới nhẹ=${counts.light_irrigation||0}, Tưới ngay=${counts.irrigate_now||0}`
    ];
    const table = `<div class=\"table-responsive\"><table class=\"table table-sm table-striped\">${head}<tbody>${body}</tbody></table></div>`;
    box.className = decision.cls;
    box.innerHTML = decision.html;
    const reasonsHtml = `<ul class=\"mb-0\">${reasons.map(r=>`<li>${r}</li>`).join('')}</ul>`;
    reason.innerHTML = `${reasonsHtml}<hr class=\"my-3\"/>${table}`;
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
      location.href = `./irrigation.html?city=${encodeURIComponent(city)}&mode=5h`;
    });
  }
  if (f3 && f3.city && btnIrr3){
    const sync3 = ()=>{ btnIrr3.disabled = !(f3.city.value && f3.city.value.trim()); };
    f3.city.addEventListener('input', sync3); sync3();
    btnIrr3.addEventListener('click', ()=>{
      const city = f3.city.value.trim();
      if(!city) return;
      location.href = `./irrigation.html?city=${encodeURIComponent(city)}&mode=3d`;
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

