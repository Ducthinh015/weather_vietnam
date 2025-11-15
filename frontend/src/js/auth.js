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
    const res = await fetch("http://localhost:5000/api/user/me", {
      headers: { "Authorization": `Bearer ${token}` }
    });

    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export function logout() {
  localStorage.removeItem('token');
  window.location.href = '/pages/login.html';
}
