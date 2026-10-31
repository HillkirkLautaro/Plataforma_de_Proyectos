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
