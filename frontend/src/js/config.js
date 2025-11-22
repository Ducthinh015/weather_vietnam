export const API_BASE = "https://agricast-backend-k9p3.onrender.com/api";
export const weatherEndpoint = `${API_BASE}/weather`;

if (typeof window !== "undefined") {
  window.API_BASE = API_BASE;
  window.weatherEndpoint = weatherEndpoint;
}
>>>>>>> 064e4f78934d17fd2d4157f7542541212b9d8470
