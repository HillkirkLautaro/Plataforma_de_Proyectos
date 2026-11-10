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

async function enviarFormularioAuth(formulario, endpoint, payload, registrar = false) {
    const boton = formulario.querySelector('button[type="submit"]');
    boton.disabled = true;
    try {
        const response = await fetch(`${API_BASE}/auth/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || data.mensaje || 'No se pudo completar la solicitud');
        if (registrar) {
            alert('Cuenta creada. Ya podés iniciar sesión.');
            window.location.href = 'login.html';
            return;
        }
        guardarSesion(data.token, data.usuario);
        window.location.href = '../index.html';
    } catch (error) {
        alert(error.message);
    } finally {
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
    if (login) login.addEventListener('submit', (event) => {
        event.preventDefault();
        enviarFormularioAuth(login, 'login', {
            username: document.getElementById('identificador').value,
            password: document.getElementById('password').value
        });
    });
});
