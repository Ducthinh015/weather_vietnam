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
    const AUTH_BASE = (window.AUTH_BASE) || (window.API_BASE ? `${window.API_BASE}/auth` : "https://agricast-backend-k9p3.onrender.com/api/auth");
    const res = await fetch(`${AUTH_BASE}/me`, {
      headers: { "Authorization": `Bearer ${token}` }
    });

    if (!res.ok) return null;
    const data = await res.json();
    return data;
  } catch {
    return null;
  }
}

export function logout() {
  localStorage.removeItem('token');
  window.location.href = '/pages/login.html';
}
