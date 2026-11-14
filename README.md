# Portfolio de Desarrolladores

## Puesta en marcha

1. Crear una base MySQL y cargar el esquema: `mysql -u <usuario> -p < database/schema.sql`. Si la base ya existe, ejecutar `database/migrate_project_skill_levels.sql` para agregar niveles de dominio a las relaciones de proyectos.
2. Crear `.env` a partir de `.env.example`. Definir un `JWT_SECRET` aleatorio de al menos 32 caracteres, credenciales DB y los valores reales de `PROFESOR_API_URL` y `GRUPO_ACCESS_KEY`. No versionar `.env`.
3. Instalar dependencias: `python3 -m pip install -r backend/requirements.txt`.
4. Desde la raíz ejecutar `python3 app.py`. El servidor escucha en `0.0.0.0:5000`; `FLASK_DEBUG` es falso por defecto.

El frontend se sirve desde Flask en el mismo origen. Para alojarlo en otro dominio, especificar `CORS_ORIGINS` como lista de orígenes separados por coma. En producción se debe usar HTTPS y un servidor WSGI detrás de Apache/reverse proxy; no activar debug.

## API

- `POST /api/auth/register`: crea la cuenta; acepta `username`, `email`, `password` y opcionalmente `nombre_completo`, `bio`.
- `POST /api/auth/login`: acepta `username` o `email` y `password`; devuelve JWT Bearer de corta duración.
- `GET /api/portfolio/perfil` y `GET/POST /api/portfolio/proyectos`, protegidos con `Authorization: Bearer <token>`.
- `GET/PUT/DELETE /api/portfolio/proyectos/<id>` aplica aislamiento por propietario del token.
- `GET /api/portafolio/<usuario_id>` expone el portfolio público.
- `GET /api/desarrolladores` lista perfiles públicos sin exponer emails; cada tarjeta enlaza a `/portfolios/<usuario_id>`, una vista HTML pública con detalles del portfolio.
- `GET /api/catalogo/lenguajes` y `/api/catalogo/tecnologias` proxyan los catálogos del profesor. No se aceptan POST/PUT en esos catálogos.

Los IDs de tecnologías y lenguajes enviados al CRUD se verifican contra la API del profesor; si el servicio no confirma los IDs, la escritura se rechaza (no hay bypass/fallback local). Contraseñas se reciben dentro de JSON sobre HTTPS y se guardan únicamente con hash scrypt.
