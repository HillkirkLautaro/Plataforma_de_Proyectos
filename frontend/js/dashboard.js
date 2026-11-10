const token = localStorage.getItem('jwt_token');
let editingProjectId = null;
const catalogSelections = { tecnologias: new Map(), lenguajes: new Map() };
const catalogData = { tecnologias: [], lenguajes: [] };

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

async function cargarOpcionesCatalogo(endpoint) {
    const response = await fetch(`${API_BASE}/catalogo/${endpoint}`);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body?.error || `No se pudo cargar el catálogo de ${endpoint}.`);
    const rows = normalizarCatalogo(body);
    catalogData[endpoint] = rows.map(item => {
        const id = Number(item.id);
        const name = item.nombre || item.name || item.descripcion || item.titulo;
        return Number.isSafeInteger(id) && id > 0 && typeof name === 'string' ? { id, name } : null;
    }).filter(Boolean);
    renderCatalogo(endpoint);
}

function renderCatalogo(type) {
    const container = document.getElementById(`${type}-options`);
    const query = document.getElementById(`${type}-search`).value.trim().toLocaleLowerCase();
    const filtered = catalogData[type].filter(item => item.name.toLocaleLowerCase().includes(query));
    container.replaceChildren();
    if (!filtered.length) {
        const empty = document.createElement('p');
        empty.className = 'catalog-empty';
        empty.textContent = catalogData[type].length ? 'No hay resultados para esa búsqueda.' : 'No se pudo cargar el catálogo.';
        container.append(empty);
    }
    filtered.forEach(item => {
        const row = document.createElement('div');
        row.className = 'catalog-option';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox'; checkbox.id = `${type}-${item.id}`;
        checkbox.checked = catalogSelections[type].has(item.id);
        checkbox.setAttribute('aria-label', `Seleccionar ${item.name}`);
        const name = document.createElement('label');
        name.className = 'catalog-option-name'; name.htmlFor = checkbox.id; name.textContent = item.name;
        const level = document.createElement('select');
        level.setAttribute('aria-label', `Nivel de dominio de ${item.name}`);
        [['básico', 'Básico'], ['intermedio', 'Intermedio'], ['avanzado', 'Avanzado']].forEach(([value, label]) => {
            const option = document.createElement('option'); option.value = value; option.textContent = label; level.append(option);
        });
        level.value = catalogSelections[type].get(item.id) || 'intermedio';
        level.disabled = !checkbox.checked;
        checkbox.addEventListener('change', () => {
            if (checkbox.checked) catalogSelections[type].set(item.id, level.value);
            else catalogSelections[type].delete(item.id);
            level.disabled = !checkbox.checked;
            actualizarContador(type);
            row.classList.toggle('is-selected', checkbox.checked);
        });
        level.addEventListener('change', () => {
            if (checkbox.checked) catalogSelections[type].set(item.id, level.value);
        });
        row.classList.toggle('is-selected', checkbox.checked);
        row.append(checkbox, name, level);
        container.append(row);
    });
    actualizarContador(type);
}

function actualizarContador(type) {
    const count = catalogSelections[type].size;
    document.getElementById(`${type}-count`).textContent = count
        ? `${count} ${count === 1 ? 'opción seleccionada' : 'opciones seleccionadas'}`
        : 'Ninguna seleccionada';
}

function relacionesSeleccionadas(type) {
    return [...catalogSelections[type]].map(([id, nivel]) => ({ id, nivel }));
}

function nombreYNivel(items, catalog) {
    if (!Array.isArray(items) || !items.length) return '—';
    return items.map(item => {
        const id = typeof item === 'object' ? item.id : item;
        const nivel = typeof item === 'object' ? item.nivel : 'intermedio';
        const name = catalog.find(option => option.id === Number(id))?.name || `#${id}`;
        return `${name} (${nivel})`;
    }).join(', ');
}

async function cargarPerfil() {
    const user = await apiRequest('/portfolio/perfil');
    localStorage.setItem('usuario', JSON.stringify(user));
    document.getElementById('developer-name').textContent = user.nombre_completo || user.username;
    document.getElementById('public-portfolio-link').href = `/portfolios/${encodeURIComponent(user.id)}`;
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
        const tech = document.createElement('small');
        tech.textContent = `Tecnologías: ${nombreYNivel(project.tecnologias, catalogData.tecnologias)} · Lenguajes: ${nombreYNivel(project.lenguajes, catalogData.lenguajes)}`;
        const links = document.createElement('div');
        links.className = 'project-links-list';
        (Array.isArray(project.links) ? project.links : []).forEach(linkData => {
            try {
                const url = new URL(linkData.url);
                if (!['http:', 'https:'].includes(url.protocol)) return;
                const anchor = document.createElement('a');
                anchor.href = url.href;
                anchor.target = '_blank';
                anchor.rel = 'noopener noreferrer';
                anchor.textContent = linkData.tipo === 'demo' ? 'Demo en vivo' : `Repositorio ${linkData.tipo}`;
                links.append(anchor);
            } catch (_) { /* Ignora URLs antiguas malformadas guardadas antes de validar. */ }
        });
        const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'Eliminar';
        const edit = document.createElement('button'); edit.type = 'button'; edit.textContent = 'Editar';
        edit.addEventListener('click', () => iniciarEdicion(project));
        remove.addEventListener('click', async () => {
            if (!confirm(`¿Eliminar «${project.nombre}»?`)) return;
            try { await apiRequest(`/portfolio/proyectos/${project.id}`, { method: 'DELETE' }); await cargarProyectos(); }
            catch (error) { alert(error.message); }
        });
        card.append(title, stage, description, tech, links, edit, remove);
        list.append(card);
    });
}

async function cargarProyectos() { mostrarProyectos(await apiRequest('/portfolio/proyectos')); }

function iniciarEdicion(project) {
    const form = document.getElementById('project-form');
    editingProjectId = project.id;
    form.elements.nombre.value = project.nombre || '';
    form.elements.descripcion.value = project.descripcion || '';
    form.elements.etapa.value = project.etapa || 'formulación';
    for (const field of ['fecha_inicio', 'fecha_fin', 'deadline']) {
        form.elements[field].value = project[field] || '';
    }
    for (const [field, relations] of [['tecnologias', project.tecnologias], ['lenguajes', project.lenguajes]]) {
        catalogSelections[field].clear();
        (Array.isArray(relations) ? relations : []).forEach(item => {
            const id = typeof item === 'object' ? Number(item.id) : Number(item);
            const level = typeof item === 'object' ? item.nivel : 'intermedio';
            if (Number.isSafeInteger(id) && id > 0) catalogSelections[field].set(id, level || 'intermedio');
        });
        renderCatalogo(field);
    }
    const existingLinks = new Map((Array.isArray(project.links) ? project.links : []).map(link => [link.tipo, link.url]));
    for (const type of ['demo', 'github', 'gitlab']) {
        document.querySelector(`[name="link_${type}"]`).value = existingLinks.get(type) || '';
    }
    form.querySelector('button[type="submit"]').textContent = 'Guardar cambios';
    document.getElementById('cancel-edit').hidden = false;
    document.getElementById('form-message').textContent = `Editando: ${project.nombre}`;
    form.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function cancelarEdicion() {
    editingProjectId = null;
    document.getElementById('project-form').reset();
    for (const type of ['tecnologias', 'lenguajes']) {
        catalogSelections[type].clear();
        renderCatalogo(type);
    }
    document.querySelector('#project-form button[type="submit"]').textContent = 'Guardar proyecto';
    document.getElementById('cancel-edit').hidden = true;
    document.getElementById('form-message').textContent = '';
}

document.addEventListener('DOMContentLoaded', async () => {
    if (!token) { window.location.replace('/views/login.html'); return; }
    document.getElementById('logout').addEventListener('click', cerrarSesion);
    document.getElementById('cancel-edit').addEventListener('click', cancelarEdicion);
    for (const type of ['tecnologias', 'lenguajes']) {
        document.getElementById(`${type}-search`).addEventListener('input', () => renderCatalogo(type));
    }
    try {
        const catalogResults = await Promise.allSettled([
            cargarOpcionesCatalogo('tecnologias'), cargarOpcionesCatalogo('lenguajes')
        ]);
        const catalogError = catalogResults.find(result => result.status === 'rejected');
        if (catalogError) document.getElementById('form-message').textContent =
            `No se pudieron cargar todos los catálogos: ${catalogError.reason.message}`;
        await cargarPerfil();
        await cargarProyectos();
    } catch (error) { document.getElementById('project-list').textContent = error.message; }

    document.getElementById('project-form').addEventListener('submit', async event => {
        event.preventDefault();
        const form = event.currentTarget;
        const message = document.getElementById('form-message');
        const data = Object.fromEntries(new FormData(form));
        try {
            data.tecnologias = relacionesSeleccionadas('tecnologias');
            data.lenguajes = relacionesSeleccionadas('lenguajes');
            data.links = ['demo', 'github', 'gitlab']
                .map(type => ({ tipo: type, url: data[`link_${type}`].trim() }))
                .filter(link => link.url);
            for (const type of ['demo', 'github', 'gitlab']) delete data[`link_${type}`];
            for (const field of ['fecha_inicio', 'fecha_fin', 'deadline']) if (!data[field]) data[field] = null;
            const wasEditing = Boolean(editingProjectId);
            const method = wasEditing ? 'PUT' : 'POST';
            const path = wasEditing ? `/portfolio/proyectos/${editingProjectId}` : '/portfolio/proyectos';
            await apiRequest(path, { method, body: JSON.stringify(data) });
            cancelarEdicion(); message.textContent = wasEditing ? 'Proyecto actualizado.' : 'Proyecto guardado.';
            await cargarProyectos();
        } catch (error) { message.textContent = error.message; }
    });
});
