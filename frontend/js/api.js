// Manejador centralizado de peticiones HTTP en JS Puro
const API_BASE = "http://localhost:5000/api";

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
    return response.json();
}
