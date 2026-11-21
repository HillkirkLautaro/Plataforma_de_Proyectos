// Manejador centralizado de peticiones HTTP en JS Puro
const API_BASE = (window.API_BASE_URL || `${window.location.origin}/api`).replace(/\/+$/, '');

async function fetchAPI(endpoint, options = {}) {
    const token = localStorage.getItem('jwt_token');
    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...options.headers
    };
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
    });
    if (response.status === 204) return null;
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || 'No se pudo completar la solicitud a la API.');
    return body;
}
