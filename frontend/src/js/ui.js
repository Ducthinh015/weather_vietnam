import { getWeather, getForecast } from './api.js';
import { renderLineChart } from './chart.js';

async function handleWeatherForm(e){
  e.preventDefault();
  const city = e.target.city.value.trim();
  const out = document.querySelector('#weatherResult');
  const err = document.querySelector('#error');
  err.textContent = '';
  out.textContent = 'Loading...';
  try{
    const data = await getWeather(city);
    out.textContent = JSON.stringify(data, null, 2);
  }catch(ex){
    out.textContent = '';
    err.textContent = ex.message;
  }
}

async function handleForecastForm(e){
  e.preventDefault();
  const city = e.target.city.value.trim();
  const out = document.querySelector('#forecastResult');
  const err = document.querySelector('#error');
  err.textContent='';
  out.textContent = 'Loading...';
  try{
    const data = await getForecast(city, 5);
    out.textContent = JSON.stringify(data, null, 2);
    const labels = data.forecast.map(x=>`+${x.after_hours}h`);
    const temps = data.forecast.map(x=>x.temperature);
    const hums = data.forecast.map(x=>x.humidity);
    renderLineChart(document.getElementById('tChart'), labels, temps, 'Temperature (C)');
    renderLineChart(document.getElementById('hChart'), labels, hums, 'Humidity (%)');
  }catch(ex){
    out.textContent = '';
    err.textContent = ex.message;
  }
}

window.addEventListener('DOMContentLoaded', ()=>{
  const wf = document.querySelector('#weatherForm');
  const ff = document.querySelector('#forecastForm');
  if(wf) wf.addEventListener('submit', handleWeatherForm);
  if(ff) ff.addEventListener('submit', handleForecastForm);
});
