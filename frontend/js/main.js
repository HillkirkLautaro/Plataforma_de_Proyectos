// Lógica de carga de vista pública
document.addEventListener('DOMContentLoaded', () => {
    console.log("Cliente web inicializado.");
    const nav = document.getElementById('nav-menu');
    const token = localStorage.getItem('jwt_token');
    const cached = JSON.parse(localStorage.getItem('usuario') || 'null');
    if (token && cached) {
        nav.innerHTML = `<a href="index.html">Explorar</a><span class="nav-user"></span><a href="/dashboard">Mi panel</a><button type="button" id="logout-nav">Cerrar sesión</button>`;
        nav.querySelector('.nav-user').textContent = cached.nombre_completo || cached.username;
        document.getElementById('logout-nav').addEventListener('click', cerrarSesion);
        fetch(`${API_BASE}/portfolio/perfil`, { headers: { Authorization: `Bearer ${token}` } })
            .then(r => { if (!r.ok) throw new Error(); return r.json(); })
            .then(user => {
                localStorage.setItem('usuario', JSON.stringify(user));
                nav.querySelector('.nav-user').textContent = user.nombre_completo || user.username;
            }).catch(() => { localStorage.removeItem('jwt_token'); localStorage.removeItem('usuario'); location.reload(); });
    }
});
