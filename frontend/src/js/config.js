const GLOBAL_BASE_URL = "https://agricast-backend-k9p3.onrender.com/api";

if (typeof window !== "undefined") {
  window.API_BASE = GLOBAL_BASE_URL;
  window.weatherEndpoint = `${window.API_BASE}/weather`;
} else if (typeof globalThis !== "undefined") {
  globalThis.API_BASE = GLOBAL_BASE_URL;
  globalThis.weatherEndpoint = `${globalThis.API_BASE}/weather`;
}