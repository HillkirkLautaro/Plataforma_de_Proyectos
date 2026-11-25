// Gestión de estado de sesión
function guardarSesion(token, usuario) {
    localStorage.setItem('jwt_token', token);
    localStorage.setItem('usuario', JSON.stringify(usuario));
}

function cerrarSesion() {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('usuario');
    window.location.href = '/index.html';
}

function mostrarMensajeAuth(texto, estado = '') {
    const node = document.getElementById('auth-message');
    if (!node) {
        if (texto) alert(texto);
        return;
    }
    node.textContent = texto;
    if (estado) node.dataset.estado = estado;
    else delete node.dataset.estado;
}

async function destinoSegunHabilidades(token) {
    try {
        const response = await fetch(`${API_BASE}/portfolio/perfil`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        if (response.status === 401) {
            localStorage.removeItem('jwt_token');
            localStorage.removeItem('usuario');
            return null;
        }
        if (!response.ok) return '/views/perfil.html';
        const perfil = await response.json();
        const tieneHabilidades =
            (Array.isArray(perfil.habilidades) && perfil.habilidades.length > 0) ||
            (Array.isArray(perfil.lenguajes) && perfil.lenguajes.length > 0);
        return tieneHabilidades ? '/views/dashboard.html' : '/views/perfil.html';
    } catch (_) {
        return '/views/perfil.html';
    }
}

async function enviarFormularioAuth(formulario, endpoint, payload, registrar = false) {
    const boton = formulario.querySelector('button[type="submit"]');
    boton.disabled = true;
    mostrarMensajeAuth('');
    try {
        const token = localStorage.getItem('jwt_token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers.Authorization = `Bearer ${token}`;
        const response = await fetch(`${API_BASE}/auth/${endpoint}`, {
            method: 'POST',
            headers,
            body: JSON.stringify(payload)
        });
        const data = await response.json().catch(() => ({}));
        if (response.status === 409 && data.redirect) {
            const destino = token ? (await destinoSegunHabilidades(token)) || '/views/dashboard.html' : '/views/dashboard.html';
            window.location.replace(destino);
            return;
        }
        if (!response.ok) throw new Error(data.error || data.mensaje || 'No se pudo completar la solicitud');
        if (registrar) {
            if (data.token && data.usuario) {
                guardarSesion(data.token, data.usuario);
                mostrarMensajeAuth('¡Registro exitoso! Redirigiendo a tu perfil...', 'success');
                setTimeout(() => window.location.replace('/views/perfil.html'), 600);
                return;
            }
            mostrarMensajeAuth(data.mensaje || 'Cuenta creada. Por favor, inicia sesión.', 'success');
            setTimeout(() => { window.location.href = 'login.html'; }, 1200);
            return;
        }
        guardarSesion(data.token, data.usuario);
        const destino = (await destinoSegunHabilidades(data.token)) || '/views/perfil.html';
        window.location.replace(destino);
    } catch (error) {
        mostrarMensajeAuth(error.message, 'error');
        boton.disabled = false;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const registro = document.getElementById('form-registro');
    if (registro) registro.addEventListener('submit', (event) => {
        event.preventDefault();
        enviarFormularioAuth(registro, 'register', {
            username: document.getElementById('username').value,
            email: document.getElementById('email').value,
            password: document.getElementById('password').value
        }, true);
    });

    const login = document.getElementById('form-login');
    const authForm = login || registro;
    const existingToken = localStorage.getItem('jwt_token');
    if (authForm && existingToken) {
        const button = authForm.querySelector('button[type="submit"]');
        button.disabled = true;
        destinoSegunHabilidades(existingToken).then(destino => {
            if (destino) {
                window.location.replace(destino);
                return;
            }
            button.disabled = false;
        }).catch(() => { button.disabled = false; });
    }
    if (login) login.addEventListener('submit', (event) => {
        event.preventDefault();
        enviarFormularioAuth(login, 'login', {
            username: document.getElementById('identificador').value,
            password: document.getElementById('password').value
        });
    });
});
