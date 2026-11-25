# DevPortfolio — Plataforma de Portafolios de Desarrolladores

Aplicación web desacoplada (Backend RESTful en **Flask + MySQL** y Frontend estático en **HTML, CSS puro moderno y JavaScript Vanilla**) que permite a desarrolladores registrarse, gestionar su perfil profesional, declarar habilidades técnicas (tecnologías y lenguajes con nivel de dominio), administrar sus proyectos y publicar un portafolio accesible para cualquier visitante.

> **Nota de desarrollo:** En la construcción y refinamiento de este proyecto se utilizó **Antigravity** como asistente de desarrollo para acelerar el proceso de elaboración de código, aplicando y validando las recomendaciones de arquitectura, diseño RESTful, seguridad, validación y buenas prácticas vistas en clase.

---

## Arquitectura y estructura del proyecto

```text
Plataforma_de_Proyectos/
├── backend/
│   ├── __init__.py                 # Fábrica de la app Flask, CORS y manejadores globales de error JSON
│   ├── app.py                      # Punto de entrada del servidor HTTP
│   ├── config/
│   │   ├── db.py                   # Pool de conexiones MySQL
│   │   └── utilsdb/db_backup.py    # Sincronización y respaldo persistente de catálogos externos en MySQL
│   ├── middlewares/
│   │   └── auth_middleware.py      # Decorador @token_requerido (validación JWT HS256)
│   ├── models/
│   │   ├── usuario.py              # Persistencia de usuarios, perfil privado y portafolio público
│   │   ├── proyecto.py             # Persistencia de proyectos y reglas de negocio (fechas, etapas, relaciones)
│   │   └── habilidad.py            # Gestión de tecnologías y lenguajes del perfil de usuario
│   ├── routes/
│   │   ├── auth_routes.py          # Registro (con auto-login JWT) e inicio de sesión
│   │   ├── catalog_routes.py       # Proxy de catálogos externos (tecnologías y lenguajes)
│   │   ├── portfolio_routes.py     # Endpoints protegidos REST de proyectos, perfil y habilidades
│   │   └── public_routes.py        # Directorio de desarrolladores y portafolio público
│   ├── schemas/                    # Esquemas JSON Schema (Draft 2020-12) para validación estricta
│   ├── services/
│   │   ├── catalog_service.py      # Caché TTL, sincronización atómica con MySQL y fallback ante caídas
│   │   └── schema_validator.py     # Validador jsonschema con traducción de errores a español
│   └── Coleccion de pruebas API/   # Colección de Bruno (OpenCollection) con 27 tests automatizados
├── database/
│   ├── schema.sql                  # Script DDL completo (tablas de usuarios, proyectos, habilidades y backup)
│   └── api_profesor_backup.sql     # DDL independiente de la tabla de respaldo de catálogos
├── docs/diagramas/                 # Diagramas PlantUML (casos de uso y clases)
├── frontend/
│   ├── index.html                  # Directorio público de desarrolladores
│   ├── views/
│   │   ├── login.html              # Inicio de sesión
│   │   ├── registro.html           # Registro de cuenta
│   │   ├── perfil.html             # Edición de perfil y habilidades (tecnologías y lenguajes)
│   │   ├── dashboard.html          # Panel privado de administración de proyectos
│   │   └── portfolio.html          # Vista pública de un portafolio individual
│   ├── css/                        # Estilos en CSS puro moderno (base, home, auth, portfolio, dashboard, perfil)
│   └── js/                         # Lógica cliente en JS Vanilla (api-config, api, auth, main, dashboard, perfil, portfolio)
└── requirements.txt                # Dependencias Python del proyecto
```

---

## Características principales

- **Autenticación segura con JWT:** Contraseñas hasheadas con `scrypt`, tokens Bearer firmados con `HS256` (`sub`, `username`, `rol`, `iss`, `iat`, `exp`, `jti`) y **inicio de sesión automático al registrarse**.
- **Flujo guiado de incorporación:** Al registrarse, el usuario es redirigido automáticamente a **Mi Perfil** (`perfil.html`) para completar su presentación y agregar habilidades; al iniciar sesión nuevamente, si ya cargó habilidades se redirige directamente a **Mis Proyectos** (`dashboard.html`).
- **API estrictamente RESTful:** Separación clara de verbos (`GET`, `POST`, `PUT` reemplazo completo, `PATCH` actualización parcial, `DELETE`), códigos de estado semánticos (`200`, `201`, `400`, `401`, `404`, `405`, `409`, `500`, `503`) y manejo idempotente de actualizaciones en MySQL.
- **Validación con JSON Schema y mensajes amigables:** Todos los payloads se validan con `jsonschema` (Draft 2020-12, `additionalProperties: false`) y cualquier error técnico se traduce automáticamente a mensajes claros en español, tanto en validaciones como en errores globales (`400`, `401`, `403`, `404`, `405`, `413`, `429`, `500`).
- **Reglas de negocio en proyectos:** Obligatoriedad de al menos una tecnología y un lenguaje, validación de rango temporal plausible (`1990-01-01` hasta 10 años a futuro), orden cronológico (`fecha_fin >= fecha_inicio`, `deadline >= fecha_inicio`) y coherencia de etapa (`formulación` / `modelado` no admiten `fecha_fin`), incluso en actualizaciones parciales (`PATCH`).
- **Sincronización y respaldo de catálogos externos:** Los recursos `tecnologias` y `lenguajes` se consultan a la API externa, se cachean en memoria con TTL configurable (`CATALOG_CACHE_TTL`) y se sincronizan atómicamente en la tabla MySQL `api_profesor_backup` (reflejando altas, modificaciones y bajas). Si la API externa falla (`Timeout`, `429`, `5xx`), el sistema sirve automáticamente el último respaldo persistido en MySQL.
- **Interfaz en CSS puro moderno:** Diseño oscuro responsivo sin frameworks externos (ni Bootstrap ni Tailwind), centralizado mediante variables CSS en `:root` (`frontend/css/base.css`), con badges diferenciados por etapa del proyecto y nivel de habilidad.

---

## Puesta en marcha

### 1. Base de datos (MySQL)
Crea la base de datos y todas las tablas ejecutando el script DDL:

```bash
mysql -u root -p < database/schema.sql
```

## API

### 2. Variables de entorno (`.env`)
Crea un archivo `.env` en la raíz del proyecto (no versionar en Git):

```env
JWT_SECRET=clave_secreta_aleatoria_de_al_menos_32_caracteres
JWT_ISSUER=portfolio-api
JWT_EXP_MINUTES=30

DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=portfolio_db

PROFESOR_API_URL=https://url-de-la-api-externa/api/v1
GRUPO_ACCESS_KEY=tu_clave_de_acceso
CATALOG_CACHE_TTL=300

# Opcional: por defecto permite http://127.0.0.1:5500, http://localhost:5500, http://127.0.0.1:5000 y http://localhost:5000
CORS_ORIGINS=http://127.0.0.1:5500,http://localhost:5500
```

### 3. Instalación de dependencias y ejecución del Backend

```bash
python -m venv .venv
# En Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# En Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
python backend/app.py
```

El servidor quedará escuchando en `http://127.0.0.1:5000` (`FLASK_DEBUG` está desactivado por defecto).

### 4. Ejecución del Frontend
El frontend es estático y está desacoplado del backend. Puedes servirlo con **Live Server** (puerto `5500`) o con Python:

```bash
python -m http.server 5500 --directory frontend
```

Verifica que `frontend/js/api-config.js` apunte a la URL de tu backend (`http://127.0.0.1:5000/api` por defecto).

---

## Endpoints de la API

### Públicos y Catálogos
| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `GET` | `/api/desarrolladores` | Listado público de desarrolladores (sin exponer correos). |
| `GET` | `/api/portafolio/<usuario_id>` | Portafolio público completo (`perfil`, `habilidades`, `lenguajes`, `proyectos`). |
| `GET` | `/api/catalogo/tecnologias` | Catálogo sincronizado de tecnologías (soporta filtro `?nombre=`). |
| `GET` | `/api/catalogo/tecnologias/<id>` | Detalle de una tecnología por ID. |
| `GET` | `/api/catalogo/lenguajes` | Catálogo sincronizado de lenguajes (soporta filtro `?nombre=`). |
| `GET` | `/api/catalogo/lenguajes/<id>` | Detalle de un lenguaje por ID. |

### Autenticación
| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Crea la cuenta (`201`) y devuelve sesión JWT lista para usar. |
| `POST` | `/api/auth/login` | Autentica por `username` o `email` + `password` y devuelve JWT (`200`). |

### Privados (requieren `Authorization: Bearer <token>`)
| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `GET` | `/api/portfolio/perfil` | Devuelve los datos del perfil autenticado junto con `habilidades` y `lenguajes`. |
| `PUT` | `/api/portfolio/perfil` | Reemplazo completo del perfil (`nombre_completo` y `bio` requeridos). |
| `PATCH` | `/api/portfolio/perfil` | Actualización parcial del perfil (`nombre_completo` y/o `bio`). |
| `POST` | `/api/portfolio/perfil/habilidades` | Agrega una tecnología o lenguaje validado contra catálogo (`201` o `409` si ya existe). |
| `PUT` | `/api/portfolio/perfil/habilidades/<tipo>/<id>` | Actualiza el `nivel` de una habilidad existente (`200` o `404`). |
| `DELETE` | `/api/portfolio/perfil/habilidades/<tipo>/<id>` | Elimina una habilidad del perfil (`200` o `404`). |
| `GET` | `/api/portfolio/proyectos` | Lista los proyectos del usuario autenticado. |
| `POST` | `/api/portfolio/proyectos` | Crea un proyecto nuevo (`201`), validando fechas, tecnologías y lenguajes. |
| `GET` | `/api/portfolio/proyectos/<id>` | Consulta un proyecto propio por ID (`200` o `404`). |
| `PUT` | `/api/portfolio/proyectos/<id>` | Reemplazo completo de un proyecto existente (`200` o `404`). |
| `PATCH` | `/api/portfolio/proyectos/<id>` | Actualización parcial de un proyecto existente (`200` o `404`). |
| `DELETE` | `/api/portfolio/proyectos/<id>` | Elimina un proyecto propio (`200` o `404`). |

---

## Pruebas automatizadas con Bruno

El repositorio incluye una colección completa en `backend/Coleccion de pruebas API/` (formato OpenCollection) con **27 tests automatizados** organizados en 5 carpetas (`01-Catalogos`, `02-Auth`, `03-Perfil-y-Habilidades`, `04-Proyectos` y `05-Publico`):

1. Inicia el servidor backend (`python backend/app.py`).
2. Abre la carpeta `backend/Coleccion de pruebas API` desde **Bruno**.
3. Selecciona el entorno **Local** (`http://127.0.0.1:5000`).
4. Ejecuta **Run** sobre toda la colección para validar de forma automática el flujo completo de extremo a extremo.
