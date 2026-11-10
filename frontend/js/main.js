// Lógica de carga de vista pública
document.addEventListener('DOMContentLoaded', () => {
    console.log("Cliente web inicializado.");
    cargarDesarrolladores();
    const nav = document.getElementById('nav-menu');
    const token = localStorage.getItem('jwt_token');
    let cached = null;
    try { cached = JSON.parse(localStorage.getItem('usuario') || 'null'); } catch (_) { localStorage.removeItem('usuario'); }
    if (token) {
        nav.innerHTML = '<a href="/">Explorar</a><span class="nav-user"></span><a href="/dashboard">Mi panel</a><button type="button" id="logout-nav">Cerrar sesión</button>';
        nav.querySelector('.nav-user').textContent = cached?.nombre_completo || cached?.username || 'Mi cuenta';
        document.getElementById('logout-nav').addEventListener('click', cerrarSesion);
        fetch(`${API_BASE}/portfolio/perfil`, { headers: { Authorization: `Bearer ${token}` } })
            .then(r => {
                if (r.status === 401) {
                    localStorage.removeItem('jwt_token');
                    localStorage.removeItem('usuario');
                    location.reload();
                    return null;
                }
                if (!r.ok) throw new Error();
                return r.json();
            })
            .then(user => {
                if (!user) return;
                localStorage.setItem('usuario', JSON.stringify(user));
                nav.querySelector('.nav-user').textContent = user.nombre_completo || user.username;
            }).catch(() => {});
    }
});

async function cargarDesarrolladores() {
    const container = document.getElementById('lista-desarrolladores');
    try {
        const response = await fetch(`${API_BASE}/desarrolladores`);
        const developers = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(developers.error || 'No se pudieron cargar los portfolios.');
        container.replaceChildren();
        if (!developers.length) {
            container.textContent = 'Todavía no hay portfolios públicos.';
            return;
        }
        developers.forEach(developer => {
            const card = document.createElement('article');
            card.className = 'card';
            const details = document.createElement('div');
            const name = document.createElement('h3');
            name.textContent = developer.nombre_completo || developer.username;
            const bio = document.createElement('p');
            bio.textContent = developer.bio || 'Desarrollador de software';
            const count = document.createElement('p');
            count.textContent = `${developer.cantidad_proyectos} proyectos publicados`;
            details.append(name, bio, count);
            const link = document.createElement('a');
            link.className = 'btn-primary portfolio-link';
            link.href = `/portfolios/${encodeURIComponent(developer.id)}`;
            link.textContent = 'Ver portfolio';
            card.append(details, link);
            container.append(card);
        });
    } catch (error) {
        container.textContent = error.message;
    }
}
