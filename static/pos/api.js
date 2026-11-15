// Shared API wrapper
const API_BASE = '/api';

function getToken() { return localStorage.getItem('token'); }
function getBranchId() { return localStorage.getItem('branchId'); }
function getUser() {
  try { return JSON.parse(localStorage.getItem('user') || 'null'); }
  catch { return null; }
}

// Helper to get CSRF token from cookies (Crucial for Django)
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

async function apiFetch(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  
  const headers = { 
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }), 
    ...(options.headers || {}) 
  };

  const token = getToken();
  if (token) headers.Authorization = `Token ${token}`;
  
  const branchId = getBranchId();
  if (branchId) headers['X-Branch-ID'] = branchId;

  // Add CSRF Token for state-changing requests
  const method = (options.method || 'GET').toUpperCase();
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }
  }

  try {
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

    if (res.status === 401) {
      localStorage.clear();
      if (location.pathname !== '/login') location.href = '/login';
      throw new Error('Unauthorized');
    }

    const text = await res.text();
    let data = null;
    
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (e) {
        // If it's not JSON, it's likely an HTML error page (500/404)
        console.error("Non-JSON response received:", text.substring(0, 200));
        if (!res.ok) throw new Error(`Server Error (${res.status}). Check console.`);
        return text;
      }
    }

    if (!res.ok) {
      const err = new Error((data && data.error) || `HTTP ${res.status}`);
      err.response = { status: res.status, data };
      throw err;
    }
    return data;
  } catch (error) {
    // Catch network errors (like CSRF blocks that prevent response)
    console.error("apiFetch network error:", error);
    throw error;
  }
}

function requireAuth() {
  if (!getToken()) { location.href = '/login'; return false; }
  return true;
}

function requireBranch() {
  if (!getBranchId()) { location.href = '/select-branch'; return false; }
  return true;
}

function requirePlatformAdmin() {
  const u = getUser();
  if (!u || u.user_type !== 'PLATFORM_ADMIN') { location.href = '/login'; return false; }
  return true;
}

function logout() {
  apiFetch('/auth/logout/', { method: 'POST' }).catch(() => {});
  localStorage.clear();
  location.href = '/login';
}

function formatCurrency(v) {
  return 'K' + parseFloat(v || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDate(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}