import { Chart, LineController, LineElement, PointElement, LinearScale, Title, CategoryScale } from 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.esm.js';
Chart.register(LineController, LineElement, PointElement, LinearScale, Title, CategoryScale);

export function renderLineChart(ctx, labels, data, label){
  if(!ctx) return;
  new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: [{ label, data, borderColor: '#60a5fa', backgroundColor: '#60a5fa22', tension: 0.2, fill: true }]},
    options: { responsive: true, plugins: { legend: { labels: { color: '#e2e8f0' } } }, scales: { x: { ticks: { color: '#94a3b8'} }, y: { ticks: { color: '#94a3b8'} } } }
  });
}
