# Portfolio de Desarrolladores

## Puesta en marcha

1. Crear una base MySQL y cargar el esquema: `mysql -u <usuario> -p < database/schema.sql`. Si la base ya existe, ejecutar `database/migrate_project_skill_levels.sql` para agregar niveles de dominio a las relaciones de proyectos.
2. Crear `.env` a partir de `.env.example`. Definir un `JWT_SECRET` aleatorio de al menos 32 caracteres, credenciales DB y los valores reales de `PROFESOR_API_URL` y `GRUPO_ACCESS_KEY`. No versionar `.env`.
3. Instalar dependencias: `python3 -m pip install -r backend/requirements.txt`.
4. Desde la raíz ejecutar `python3 app.py`. El servidor expone sólo la API en `0.0.0.0:5000`; `FLASK_DEBUG` es falso por defecto.

El frontend está desacoplado y debe servirse como sitio estático (por ejemplo, en desarrollo: `python3 -m http.server 8080 --directory frontend`). Configurar `frontend/js/api-config.js` con la URL absoluta de la API, incluyendo `/api` (por defecto `http://localhost:5000/api`). En `.env`, definir `CORS_ORIGINS` con el origen exacto del frontend, por ejemplo `http://localhost:8080`; en producción usar HTTPS y el dominio real. El backend debe ejecutarse con un servidor WSGI detrás de Apache/reverse proxy; no activar debug.

## API

- `POST /api/auth/register`: crea la cuenta; acepta `username`, `email`, `password` y opcionalmente `nombre_completo`, `bio`.
- `POST /api/auth/login`: acepta `username` o `email` y `password`; devuelve JWT Bearer de corta duración.
- `GET /api/portfolio/perfil` y `GET/POST /api/portfolio/proyectos`, protegidos con `Authorization: Bearer <token>`.
- `GET/PUT/DELETE /api/portfolio/proyectos/<id>` aplica aislamiento por propietario del token.
- `GET /api/portafolio/<usuario_id>` expone el portfolio público.
- `GET /api/desarrolladores` lista perfiles públicos sin exponer emails. El frontend estático muestra el detalle en `/views/portfolio.html?id=<usuario_id>`, que consume `GET /api/portafolio/<usuario_id>`.
- `GET /api/catalogo/lenguajes` y `/api/catalogo/tecnologias` proxyan los catálogos del profesor. No se aceptan POST/PUT en esos catálogos.

Los IDs de tecnologías y lenguajes enviados al CRUD se verifican contra la API del profesor; si el servicio no confirma los IDs, la escritura se rechaza (no hay bypass/fallback local). Contraseñas se reciben dentro de JSON sobre HTTPS y se guardan únicamente con hash scrypt.
