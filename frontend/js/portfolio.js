function catalogRows(body) {
    if (Array.isArray(body)) return body;
    return body?.data || body?.results || body?.items || body?.tecnologias || body?.lenguajes || [];
}

async function obtenerCatalogo(path) {
    try {
        const response = await fetch(`${API_BASE}/catalogo/${path}`);
        if (!response.ok) return new Map();
        const rows = catalogRows(await response.json());
        return new Map(rows.map(row => [Number(row.id), row.nombre || row.name || row.descripcion || `#${row.id}`]));
    } catch (_) { return new Map(); }
}

function textoIds(ids, catalog) {
    if (!Array.isArray(ids) || ids.length === 0) return '—';
    return ids.map(item => {
        const id = typeof item === 'object' ? item.id : item;
        const level = typeof item === 'object' ? item.nivel : null;
        const name = catalog.get(Number(id)) || `#${id}`;
        return level ? `${name} (${level})` : name;
    }).join(', ');
}

function renderProject(project, techCatalog, languageCatalog) {
    const card = document.createElement('article');
    card.className = 'public-project';
    const title = document.createElement('h3'); title.textContent = project.nombre;
    const stage = document.createElement('strong'); stage.textContent = project.etapa;
    const description = document.createElement('p'); description.textContent = project.descripcion || 'Sin descripción.';
    const technologies = document.createElement('p');
    technologies.className = 'project-meta';
    technologies.textContent = `Tecnologías: ${textoIds(project.tecnologias, techCatalog)}`;
    const languages = document.createElement('p');
    languages.className = 'project-meta';
    languages.textContent = `Lenguajes: ${textoIds(project.lenguajes, languageCatalog)}`;
    const dates = document.createElement('p');
    dates.className = 'project-meta';
    dates.textContent = project.deadline ? `Fecha límite: ${project.deadline}` : '';
    const links = document.createElement('div');
    links.className = 'tag-list';
    (Array.isArray(project.links) ? project.links : []).forEach(linkData => {
        try {
            const url = new URL(linkData.url);
            if (!['http:', 'https:'].includes(url.protocol)) return;
            const anchor = document.createElement('a');
            anchor.className = 'tag';
            anchor.href = url.href;
            anchor.target = '_blank';
            anchor.rel = 'noopener noreferrer';
            anchor.textContent = linkData.tipo === 'demo' ? 'Demo en vivo' : `Repositorio ${linkData.tipo}`;
            links.append(anchor);
        } catch (_) { /* Ignora links existentes con URL inválida. */ }
    });
    card.append(title, stage, description, technologies, languages, dates, links);
    return card;
}

document.addEventListener('DOMContentLoaded', async () => {
    await configurarMenuSesion();
    const id = Number(window.location.pathname.split('/').filter(Boolean).at(-1));
    const profileNode = document.getElementById('profile');
    const projectsNode = document.getElementById('projects');
    const skillsNode = document.getElementById('skills');
    if (!Number.isSafeInteger(id) || id <= 0) {
        profileNode.textContent = 'El portfolio solicitado no es válido.';
        return;
    }
    try {
        const response = await fetch(`${API_BASE}/portafolio/${id}`);
        const result = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(result.error || 'No se pudo encontrar este portfolio.');

        const [techCatalog, languageCatalog] = await Promise.all([
            obtenerCatalogo('tecnologias'), obtenerCatalogo('lenguajes')
        ]);
        const profile = result.perfil;
        profileNode.replaceChildren();
        const name = document.createElement('h2');
        name.textContent = profile.nombre_completo || profile.username;
        const username = document.createElement('p'); username.textContent = `@${profile.username}`;
        const bio = document.createElement('p'); bio.textContent = profile.bio || 'Portfolio de desarrollador.';
        profileNode.append(name, username, bio);

        projectsNode.replaceChildren();
        if (!result.proyectos?.length) projectsNode.textContent = 'Este desarrollador todavía no publicó proyectos.';
        else result.proyectos.forEach(project => projectsNode.append(renderProject(project, techCatalog, languageCatalog)));

        skillsNode.replaceChildren();
        if (!result.habilidades?.length) skillsNode.textContent = 'Sin habilidades publicadas.';
        else result.habilidades.forEach(skill => {
            const tag = document.createElement('span');
            tag.className = 'tag';
            tag.textContent = `${techCatalog.get(Number(skill.tecnologia_id)) || `Tecnología #${skill.tecnologia_id}`} · ${skill.nivel}`;
            skillsNode.append(tag);
        });
        document.title = `${profile.nombre_completo || profile.username} | DevPortfolio`;
    } catch (error) {
        profileNode.replaceChildren();
        const message = document.createElement('p');
        message.className = 'error-message';
        message.textContent = error.message;
        profileNode.append(message);
    }
});

async function configurarMenuSesion() {
    const nav = document.getElementById('nav-menu');
    const token = localStorage.getItem('jwt_token');
    if (!token) return;
    try {
        const response = await fetch(`${API_BASE}/portfolio/perfil`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        if (response.status === 401) {
            localStorage.removeItem('jwt_token');
            localStorage.removeItem('usuario');
            return;
        }
        if (!response.ok) return;
        const user = await response.json();
        localStorage.setItem('usuario', JSON.stringify(user));
        nav.replaceChildren();
        const directory = document.createElement('a'); directory.href = '/'; directory.textContent = 'Todos los desarrolladores';
        const username = document.createElement('span'); username.textContent = user.nombre_completo || user.username;
        const dashboard = document.createElement('a'); dashboard.href = '/dashboard'; dashboard.textContent = 'Mi panel';
        const logout = document.createElement('button'); logout.type = 'button'; logout.textContent = 'Cerrar sesión';
        logout.addEventListener('click', cerrarSesion);
        nav.append(directory, username, dashboard, logout);
    } catch (_) {
        // Si el backend no responde temporalmente, se conserva la vista pública.
    }
}
