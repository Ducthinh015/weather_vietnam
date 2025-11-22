import { API_BASE } from './config.js';

const AUTH_BASE = `${API_BASE}/auth`;

export function getToken() {
  return localStorage.getItem('token');
}

export function isLoggedIn() {
  return !!localStorage.getItem('token');
}

export async function getCurrentUser() {
  const token = getToken();
  if (!token) return null;

  try {
    const res = await fetch(`${AUTH_BASE}/me`, {
      headers: { "Authorization": `Bearer ${token}` }
    });

    if (!res.ok) return null;
    const data = await res.json();
    return data?.user || data;
  } catch {
    return null;
  }
}

export function logout() {
  localStorage.removeItem('token');
  window.location.href = '/pages/login.html';
}
