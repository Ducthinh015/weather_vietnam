import Chart from 'https://esm.sh/chart.js@4.4.1/auto';

const _charts = new Map();

export function renderLineChart(ctx, labels, data, label){
  if(!ctx) return;
  const key = ctx.id || ctx.getAttribute('id') || ctx;
  const prev = _charts.get(key);
  if (prev && typeof prev.destroy === 'function') {
    try{ prev.destroy(); }catch(_){  }
  }
  const inst = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: [{ label, data, borderColor: '#60a5fa', backgroundColor: '#60a5fa22', tension: 0.2, fill: true }]},
    options: { responsive: true, plugins: { legend: { labels: { color: '#e2e8f0' } } }, scales: { x: { ticks: { color: '#94a3b8'} }, y: { ticks: { color: '#94a3b8'} } } }
  });
  _charts.set(key, inst);
  return inst;
}

export function renderMultiLineChart(ctx, labels, datasets){
  if(!ctx) return;
  const key = ctx.id || ctx.getAttribute('id') || ctx;
  const prev = _charts.get(key);
  if (prev && typeof prev.destroy === 'function') {
    try{ prev.destroy(); }catch(_){  }
  }
  const inst = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: { responsive: true, plugins: { legend: { labels: { color: '#e2e8f0' } } }, scales: { x: { ticks: { color: '#94a3b8'} }, y: { ticks: { color: '#94a3b8'} } } }
  });
  _charts.set(key, inst);
  return inst;
}

