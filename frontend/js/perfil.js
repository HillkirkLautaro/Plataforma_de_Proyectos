const token = localStorage.getItem('jwt_token');
const catalogos = { tecnologias: [], lenguajes: [] };
let habilidadesUsuario = { tecnologias: [], lenguajes: [] };

function authHeaders() {
    return { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };
}

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: { ...authHeaders(), ...(options.headers || {}) },
    });
    const body = response.status === 204 ? null : await response.json().catch(() => ({}));
    if (response.status === 401) {
        cerrarSesion();
        throw new Error(body?.error || 'Tu sesión ha expirado. Por favor, inicia sesión nuevamente.');
    }
    if (!response.ok) {
        throw new Error(body?.error || 'No se pudo completar la operación.');
    }
    return body;
}

function mostrarEstado(elementId, texto, estado = '') {
    const node = document.getElementById(elementId);
    node.textContent = texto;
    if (estado) node.dataset.estado = estado;
    else delete node.dataset.estado;
}

function normalizarListaCatalogo(body) {
    const rows = Array.isArray(body) ? body : (body?.data || body?.results || body?.items || []);
    if (!Array.isArray(rows)) return [];
    return rows
        .map(item => {
            const id = Number(item.id);
            const name = item.nombre || item.name || item.descripcion || item.titulo;
            return Number.isSafeInteger(id) && id > 0 && typeof name === 'string' ? { id, name } : null;
        })
        .filter(Boolean);
}

async function cargarCatalogo(endpoint) {
    const response = await fetch(`${API_BASE}/catalogo/${endpoint}`);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(body?.error || `No se pudo cargar el catálogo de ${endpoint}.`);
    }
    catalogos[endpoint] = normalizarListaCatalogo(body);
}

function poblarSelectCatalogo() {
    const tipo = document.getElementById('habilidad-tipo').value;
    const select = document.getElementById('habilidad-item');
    const lista = tipo === 'tecnologia' ? catalogos.tecnologias : catalogos.lenguajes;
    select.replaceChildren();

    if (!lista.length) {
        const emptyOpt = document.createElement('option');
        emptyOpt.value = '';
        emptyOpt.textContent = 'Catálogo no disponible';
        select.append(emptyOpt);
        select.disabled = true;
        return;
    }

    select.disabled = false;
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = tipo === 'tecnologia' ? 'Selecciona una tecnología...' : 'Selecciona un lenguaje...';
    select.append(placeholder);

    lista.forEach(item => {
        const option = document.createElement('option');
        option.value = String(item.id);
        option.textContent = item.name;
        select.append(option);
    });
}

function actualizarContadores() {
    const nombreInput = document.getElementById('nombre_completo');
    const bioInput = document.getElementById('bio');
    document.getElementById('nombre-count').textContent = `${nombreInput.value.length} / 100`;
    document.getElementById('bio-count').textContent = `${bioInput.value.length} / 10000`;
}

function obtenerNombreCatalogo(tipo, id) {
    const lista = tipo === 'tecnologia' ? catalogos.tecnologias : catalogos.lenguajes;
    return lista.find(item => item.id === Number(id))?.name || `#${id}`;
}

function renderizarGrupoHabilidades(tipo, containerId, items) {
    const container = document.getElementById(containerId);
    container.replaceChildren();

    if (!Array.isArray(items) || !items.length) {
        const empty = document.createElement('p');
        empty.className = 'skill-empty';
        empty.textContent = tipo === 'tecnologia'
            ? 'Todavía no agregaste tecnologías a tu perfil.'
            : 'Todavía no agregaste lenguajes a tu perfil.';
        container.append(empty);
        return;
    }

    items.forEach(skill => {
        const row = document.createElement('div');
        row.className = 'skill-item';

        const info = document.createElement('div');
        info.className = 'skill-info';

        const name = document.createElement('span');
        name.className = 'skill-name';
        const nombreCatalogo = obtenerNombreCatalogo(tipo, skill.id);
        name.textContent = nombreCatalogo;

        const badge = document.createElement('span');
        badge.className = 'skill-badge';
        badge.dataset.nivel = skill.nivel;
        badge.textContent = skill.nivel;

        info.append(name, badge);

        const controls = document.createElement('div');
        controls.className = 'skill-controls';

        const levelSelect = document.createElement('select');
        levelSelect.className = 'skill-level-select';
        levelSelect.setAttribute('aria-label', `Cambiar nivel de ${nombreCatalogo}`);
        [['básico', 'Básico'], ['intermedio', 'Intermedio'], ['avanzado', 'Avanzado']].forEach(([value, label]) => {
            const opt = document.createElement('option');
            opt.value = value;
            opt.textContent = label;
            levelSelect.append(opt);
        });
        levelSelect.value = skill.nivel;

        levelSelect.addEventListener('change', async () => {
            const nuevoNivel = levelSelect.value;
            levelSelect.disabled = true;
            try {
                const res = await apiRequest(`/portfolio/perfil/habilidades/${tipo}/${Number(skill.id)}`, {
                    method: 'PUT',
                    body: JSON.stringify({ nivel: nuevoNivel }),
                });
                skill.nivel = nuevoNivel;
                badge.dataset.nivel = nuevoNivel;
                badge.textContent = nuevoNivel;
                mostrarEstado('habilidad-message', res.mensaje || 'Nivel actualizado correctamente.', 'success');
            } catch (error) {
                levelSelect.value = skill.nivel;
                mostrarEstado('habilidad-message', error.message, 'error');
            } finally {
                levelSelect.disabled = false;
            }
        });

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn-remove-skill';
        removeBtn.textContent = 'Eliminar';
        removeBtn.addEventListener('click', async () => {
            if (!confirm(`¿Quitar «${nombreCatalogo}» de tu perfil?`)) return;
            removeBtn.disabled = true;
            try {
                const res = await apiRequest(`/portfolio/perfil/habilidades/${tipo}/${Number(skill.id)}`, {
                    method: 'DELETE',
                });
                if (tipo === 'tecnologia') {
                    habilidadesUsuario.tecnologias = habilidadesUsuario.tecnologias.filter(h => Number(h.id) !== Number(skill.id));
                } else {
                    habilidadesUsuario.lenguajes = habilidadesUsuario.lenguajes.filter(h => Number(h.id) !== Number(skill.id));
                }
                renderizarHabilidades();
                mostrarEstado('habilidad-message', res.mensaje || 'Habilidad eliminada correctamente.', 'success');
            } catch (error) {
                mostrarEstado('habilidad-message', error.message, 'error');
                removeBtn.disabled = false;
            }
        });

        controls.append(levelSelect, removeBtn);
        row.append(info, controls);
        container.append(row);
    });
}

function renderizarHabilidades() {
    renderizarGrupoHabilidades('tecnologia', 'lista-tecnologias', habilidadesUsuario.tecnologias);
    renderizarGrupoHabilidades('lenguaje', 'lista-lenguajes', habilidadesUsuario.lenguajes);
    const btnProyectos = document.getElementById('btn-ir-proyectos');
    if (btnProyectos) {
        const tieneHabilidades =
            habilidadesUsuario.tecnologias.length > 0 || habilidadesUsuario.lenguajes.length > 0;
        btnProyectos.hidden = !tieneHabilidades;
    }
}

async function cargarPerfil() {
    const data = await apiRequest('/portfolio/perfil');
    localStorage.setItem('usuario', JSON.stringify({
        id: data.id,
        username: data.username,
        email: data.email,
        nombre_completo: data.nombre_completo,
        bio: data.bio,
    }));

    document.getElementById('perfil-username').textContent = `@${data.username}`;
    document.getElementById('perfil-email').textContent = data.email;
    document.getElementById('nombre_completo').value = data.nombre_completo || '';
    document.getElementById('bio').value = data.bio || '';
    document.getElementById('public-portfolio-link').href = `/views/portfolio.html?id=${encodeURIComponent(data.id)}`;
    actualizarContadores();

    habilidadesUsuario = {
        tecnologias: Array.isArray(data.habilidades) ? data.habilidades : [],
        lenguajes: Array.isArray(data.lenguajes) ? data.lenguajes : [],
    };
    renderizarHabilidades();
}

document.addEventListener('DOMContentLoaded', async () => {
    if (!token) {
        window.location.replace('/views/login.html');
        return;
    }

    document.getElementById('logout').addEventListener('click', cerrarSesion);
    document.getElementById('nombre_completo').addEventListener('input', actualizarContadores);
    document.getElementById('bio').addEventListener('input', actualizarContadores);
    document.getElementById('habilidad-tipo').addEventListener('change', poblarSelectCatalogo);

    const catalogResults = await Promise.allSettled([
        cargarCatalogo('tecnologias'),
        cargarCatalogo('lenguajes'),
    ]);
    poblarSelectCatalogo();

    const catalogError = catalogResults.find(r => r.status === 'rejected');
    if (catalogError) {
        mostrarEstado('habilidad-message', catalogError.reason.message, 'error');
    }

    try {
        await cargarPerfil();
    } catch (error) {
        mostrarEstado('perfil-message', error.message, 'error');
    }

    document.getElementById('perfil-form').addEventListener('submit', async event => {
        event.preventDefault();
        const btn = document.getElementById('btn-guardar-perfil');
        btn.disabled = true;
        try {
            const payload = {
                nombre_completo: document.getElementById('nombre_completo').value.trim(),
                bio: document.getElementById('bio').value.trim(),
            };
            const res = await apiRequest('/portfolio/perfil', {
                method: 'PUT',
                body: JSON.stringify(payload),
            });
            if (res.perfil) {
                localStorage.setItem('usuario', JSON.stringify(res.perfil));
            }
            mostrarEstado('perfil-message', res.mensaje || 'Perfil actualizado correctamente.', 'success');
        } catch (error) {
            mostrarEstado('perfil-message', error.message, 'error');
        } finally {
            btn.disabled = false;
        }
    });

    document.getElementById('habilidad-form').addEventListener('submit', async event => {
        event.preventDefault();
        const tipo = document.getElementById('habilidad-tipo').value;
        const itemId = Number(document.getElementById('habilidad-item').value);
        const nivel = document.getElementById('habilidad-nivel').value;

        if (!Number.isSafeInteger(itemId) || itemId < 1) {
            mostrarEstado('habilidad-message', 'Selecciona una opción del catálogo antes de agregarla.', 'error');
            return;
        }

        const btn = document.getElementById('btn-agregar-habilidad');
        btn.disabled = true;
        try {
            const res = await apiRequest('/portfolio/perfil/habilidades', {
                method: 'POST',
                body: JSON.stringify({ tipo, id: itemId, nivel }),
            });
            const lista = tipo === 'tecnologia' ? habilidadesUsuario.tecnologias : habilidadesUsuario.lenguajes;
            const existente = lista.find(h => Number(h.id) === itemId);
            if (existente) {
                existente.nivel = nivel;
            } else {
                lista.push({ id: itemId, nivel });
            }
            renderizarHabilidades();
            mostrarEstado('habilidad-message', res.mensaje || 'Habilidad guardada correctamente.', 'success');
        } catch (error) {
            mostrarEstado('habilidad-message', error.message, 'error');
        } finally {
            btn.disabled = false;
        }
    });
});
