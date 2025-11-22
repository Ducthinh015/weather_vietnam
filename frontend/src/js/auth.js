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
    const AUTH_BASE = (window.AUTH_BASE) || (window.API_BASE ? `${window.API_BASE}/auth` : "https://agricast-ai-vn-838179290451.asia-southeast1.run.app/api/auth");
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
