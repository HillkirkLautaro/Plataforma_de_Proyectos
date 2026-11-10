const token = localStorage.getItem('jwt_token');
const userCache = JSON.parse(localStorage.getItem('usuario') || 'null');

function authHeaders() { return { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }; }
async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers: { ...authHeaders(), ...(options.headers || {}) } });
    const body = response.status === 204 ? null : await response.json().catch(() => ({}));
    if (response.status === 401) { cerrarSesion(); throw new Error('Sesión vencida'); }
    if (!response.ok) throw new Error(body?.error || 'Falló la operación');
    return body;
}

function normalizarCatalogo(body) {
    const rows = Array.isArray(body) ? body : (body?.data || body?.results || body?.items || []);
    if (!Array.isArray(rows)) throw new Error('La API devolvió un catálogo con formato inválido.');
    return rows;
}

async function cargarOpcionesCatalogo(endpoint, selectId) {
    const response = await fetch(`${API_BASE}/catalogo/${endpoint}`);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body?.error || `No se pudo cargar el catálogo de ${endpoint}.`);
    const select = document.getElementById(selectId);
    const rows = normalizarCatalogo(body);
    select.replaceChildren();
    rows.forEach(item => {
        const id = Number(item.id);
        const name = item.nombre || item.name || item.descripcion;
        if (!Number.isSafeInteger(id) || id <= 0 || typeof name !== 'string') return;
        const option = document.createElement('option');
        option.value = String(id);
        option.textContent = name;
        select.append(option);
    });
    if (!select.options.length) {
        const option = document.createElement('option');
        option.disabled = true;
        option.textContent = 'No hay opciones disponibles';
        select.append(option);
    }
}

function idsSeleccionados(selectId) {
    return [...document.getElementById(selectId).selectedOptions]
        .filter(option => !option.disabled)
        .map(option => Number(option.value));
}

async function cargarPerfil() {
    const user = await apiRequest('/portfolio/perfil');
    localStorage.setItem('usuario', JSON.stringify(user));
    document.getElementById('developer-name').textContent = user.nombre_completo || user.username;
}

function mostrarProyectos(projects) {
    const list = document.getElementById('project-list');
    list.replaceChildren();
    if (!projects.length) { list.textContent = 'Todavía no agregaste proyectos.'; return; }
    projects.forEach(project => {
        const card = document.createElement('article');
        card.className = 'project-card';
        const title = document.createElement('h3'); title.textContent = project.nombre;
        const stage = document.createElement('strong'); stage.textContent = project.etapa;
        const description = document.createElement('p'); description.textContent = project.descripcion || 'Sin descripción';
        const tech = document.createElement('small'); tech.textContent = `Tecnologías: ${project.tecnologias || '—'} · Lenguajes: ${project.lenguajes || '—'}`;
        const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'Eliminar';
        remove.addEventListener('click', async () => {
            if (!confirm(`¿Eliminar «${project.nombre}»?`)) return;
            try { await apiRequest(`/portfolio/proyectos/${project.id}`, { method: 'DELETE' }); await cargarProyectos(); }
            catch (error) { alert(error.message); }
        });
        card.append(title, stage, description, tech, remove);
        list.append(card);
    });
}

async function cargarProyectos() { mostrarProyectos(await apiRequest('/portfolio/proyectos')); }

document.addEventListener('DOMContentLoaded', async () => {
    if (!token) { window.location.replace('/views/login.html'); return; }
    document.getElementById('logout').addEventListener('click', cerrarSesion);
    try {
        await Promise.all([
            cargarOpcionesCatalogo('tecnologias', 'tecnologias'),
            cargarOpcionesCatalogo('lenguajes', 'lenguajes')
        ]);
        await cargarPerfil();
        await cargarProyectos();
    } catch (error) { document.getElementById('project-list').textContent = error.message; }

    document.getElementById('project-form').addEventListener('submit', async event => {
        event.preventDefault();
        const form = event.currentTarget;
        const message = document.getElementById('form-message');
        const data = Object.fromEntries(new FormData(form));
        try {
            data.tecnologias = idsSeleccionados('tecnologias');
            data.lenguajes = idsSeleccionados('lenguajes');
            for (const field of ['fecha_inicio', 'fecha_fin', 'deadline']) if (!data[field]) data[field] = null;
            await apiRequest('/portfolio/proyectos', { method: 'POST', body: JSON.stringify(data) });
            form.reset(); message.textContent = 'Proyecto guardado.'; await cargarProyectos();
        } catch (error) { message.textContent = error.message; }
    });
});
