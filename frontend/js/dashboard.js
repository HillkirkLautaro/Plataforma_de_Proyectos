const token = localStorage.getItem('jwt_token');
let editingProjectId = null;
const catalogSelections = { tecnologias: new Map(), lenguajes: new Map() };
const catalogData = { tecnologias: [], lenguajes: [] };
const FECHA_MINIMA_PROYECTO = '1990-01-01';
const ETAPAS_SIN_FECHA_FIN = new Set(['formulación', 'modelado']);

function obtenerFechaMaximaProyecto() {
    const hoy = new Date();
    const anio = hoy.getFullYear() + 10;
    const mes = String(hoy.getMonth() + 1).padStart(2, '0');
    const diaMaxMes = new Date(anio, hoy.getMonth() + 1, 0).getDate();
    const dia = String(Math.min(hoy.getDate(), diaMaxMes)).padStart(2, '0');
    return `${anio}-${mes}-${dia}`;
}

function normalizarFechaInput(valor) {
    if (!valor) return '';
    if (typeof valor === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(valor)) return valor;
    const parsed = new Date(valor);
    if (Number.isNaN(parsed.getTime())) return '';
    return parsed.toISOString().slice(0, 10);
}

function sincronizarLimitesFechas(form) {
    const fechaMax = obtenerFechaMaximaProyecto();
    const inicioInput = form.elements.fecha_inicio;
    const finInput = form.elements.fecha_fin;
    const deadlineInput = form.elements.deadline;

    for (const input of [inicioInput, finInput, deadlineInput]) {
        input.min = FECHA_MINIMA_PROYECTO;
        input.max = fechaMax;
    }

    const minRelativo = inicioInput.value && inicioInput.value >= FECHA_MINIMA_PROYECTO
        ? inicioInput.value
        : FECHA_MINIMA_PROYECTO;
    finInput.min = minRelativo;
    deadlineInput.min = minRelativo;
}

function mostrarMensajeFormulario(texto, estado = '') {
    const message = document.getElementById('form-message');
    message.textContent = texto;
    if (estado) message.dataset.estado = estado;
    else delete message.dataset.estado;
}

function validarFormularioProyecto(data) {
    if (!data.tecnologias.length && !data.lenguajes.length) {
        return 'El proyecto debe incluir al menos una tecnología y un lenguaje de programación.';
    }
    if (!data.tecnologias.length) {
        return 'Debes seleccionar al menos una tecnología para el proyecto.';
    }
    if (!data.lenguajes.length) {
        return 'Debes seleccionar al menos un lenguaje de programación para el proyecto.';
    }

    const fechaMax = obtenerFechaMaximaProyecto();
    const camposFecha = [
        ['fecha_inicio', 'fecha de inicio'],
        ['fecha_fin', 'fecha de finalización'],
        ['deadline', 'fecha límite'],
    ];

    for (const [clave, etiqueta] of camposFecha) {
        const valor = data[clave];
        if (!valor) continue;
        if (valor < FECHA_MINIMA_PROYECTO) {
            return `La ${etiqueta} no puede ser anterior al 1 de enero de 1990.`;
        }
        if (valor > fechaMax) {
            return `La ${etiqueta} no puede superar los 10 años a partir de hoy (${fechaMax}).`;
        }
    }

    if (data.fecha_inicio && data.fecha_fin && data.fecha_fin < data.fecha_inicio) {
        return 'La fecha de finalización no puede ser anterior a la fecha de inicio.';
    }
    if (data.fecha_inicio && data.deadline && data.deadline < data.fecha_inicio) {
        return 'La fecha límite no puede ser anterior a la fecha de inicio.';
    }
    if (ETAPAS_SIN_FECHA_FIN.has(data.etapa) && data.fecha_fin) {
        return 'No puedes asignar una fecha de finalización mientras el proyecto está en etapa de formulación o modelado.';
    }
    return null;
}

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
    const vacio = type === 'tecnologias' ? 'Ninguna seleccionada (obligatorio)' : 'Ninguno seleccionado (obligatorio)';
    document.getElementById(`${type}-count`).textContent = count
        ? `${count} ${count === 1 ? 'opción seleccionada' : 'opciones seleccionadas'}`
        : vacio;
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
    document.getElementById('public-portfolio-link').href = `/views/portfolio.html?id=${encodeURIComponent(user.id)}`;
}

function mostrarProyectos(projects) {
    const list = document.getElementById('project-list');
    list.replaceChildren();
    if (!projects.length) { list.textContent = 'Todavía no agregaste proyectos.'; return; }
    projects.forEach(project => {
        const card = document.createElement('article');
        card.className = 'project-card';
        const title = document.createElement('h3'); title.textContent = project.nombre;
        const stage = document.createElement('strong');
        stage.className = 'stage-badge';
        stage.dataset.etapa = project.etapa;
        stage.textContent = project.etapa;
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
        const actions = document.createElement('div');
        actions.className = 'project-actions';
        const edit = document.createElement('button'); edit.type = 'button'; edit.className = 'btn-edit'; edit.textContent = 'Editar';
        const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'btn-delete'; remove.textContent = 'Eliminar';
        edit.addEventListener('click', () => iniciarEdicion(project));
        remove.addEventListener('click', async () => {
            if (!confirm(`¿Eliminar «${project.nombre}»?`)) return;
            try { await apiRequest(`/portfolio/proyectos/${project.id}`, { method: 'DELETE' }); await cargarProyectos(); }
            catch (error) { alert(error.message); }
        });
        actions.append(edit, remove);
        card.append(title, stage, description, tech, links, actions);
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
        form.elements[field].value = normalizarFechaInput(project[field]);
    }
    sincronizarLimitesFechas(form);
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
    mostrarMensajeFormulario(`Editando: ${project.nombre}`);
    form.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function cancelarEdicion() {
    editingProjectId = null;
    const form = document.getElementById('project-form');
    form.reset();
    sincronizarLimitesFechas(form);
    for (const type of ['tecnologias', 'lenguajes']) {
        catalogSelections[type].clear();
        renderCatalogo(type);
    }
    document.querySelector('#project-form button[type="submit"]').textContent = 'Guardar proyecto';
    document.getElementById('cancel-edit').hidden = true;
    mostrarMensajeFormulario('');
}

document.addEventListener('DOMContentLoaded', async () => {
    if (!token) { window.location.replace('/views/login.html'); return; }
    const projectForm = document.getElementById('project-form');
    sincronizarLimitesFechas(projectForm);
    projectForm.elements.fecha_inicio.addEventListener('change', () => sincronizarLimitesFechas(projectForm));
    projectForm.elements.fecha_inicio.addEventListener('input', () => sincronizarLimitesFechas(projectForm));
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
        if (catalogError) mostrarMensajeFormulario(
            `No se pudieron cargar todos los catálogos: ${catalogError.reason.message}`,
            'error'
        );
        await cargarPerfil();
        await cargarProyectos();
    } catch (error) { document.getElementById('project-list').textContent = error.message; }

    projectForm.addEventListener('submit', async event => {
        event.preventDefault();
        const form = event.currentTarget;
        const data = Object.fromEntries(new FormData(form));
        try {
            data.tecnologias = relacionesSeleccionadas('tecnologias');
            data.lenguajes = relacionesSeleccionadas('lenguajes');
            data.links = ['demo', 'github', 'gitlab']
                .map(type => ({ tipo: type, url: data[`link_${type}`].trim() }))
                .filter(link => link.url);
            for (const type of ['demo', 'github', 'gitlab']) delete data[`link_${type}`];
            for (const field of ['fecha_inicio', 'fecha_fin', 'deadline']) if (!data[field]) data[field] = null;

            const errorValidacion = validarFormularioProyecto(data);
            if (errorValidacion) {
                mostrarMensajeFormulario(errorValidacion, 'error');
                return;
            }

            const wasEditing = Boolean(editingProjectId);
            const method = wasEditing ? 'PUT' : 'POST';
            const path = wasEditing ? `/portfolio/proyectos/${editingProjectId}` : '/portfolio/proyectos';
            await apiRequest(path, { method, body: JSON.stringify(data) });
            cancelarEdicion();
            mostrarMensajeFormulario(wasEditing ? 'Proyecto actualizado correctamente.' : 'Proyecto guardado correctamente.', 'success');
            await cargarProyectos();
        } catch (error) { mostrarMensajeFormulario(error.message, 'error'); }
    });
});
