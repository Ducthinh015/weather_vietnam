export const API_BASE = "https://agricast-backend-k9p3.onrender.com/api";
export const weatherEndpoint = `${API_BASE}/weather`;

if (typeof window !== "undefined") {
  window.API_BASE = API_BASE;
  window.weatherEndpoint = weatherEndpoint;
}
