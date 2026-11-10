from datetime import date
from urllib.parse import urlparse

from flask import Blueprint, current_app, jsonify, request
from middlewares.auth_middleware import token_requerido
from models.proyecto import Proyecto
from services.catalog_service import CatalogUnavailable, validar_ids_catalogo

portfolio_bp = Blueprint("portfolio_bp", __name__)


def _validar_payload(data, crear=False):
    if not isinstance(data, dict):
        return "Se requiere un objeto JSON"
    if crear and not isinstance(data.get("nombre"), str):
        return "nombre es obligatorio y debe ser texto"
    if "nombre" in data and (not isinstance(data["nombre"], str) or not 1 <= len(data["nombre"].strip()) <= 120):
        return "nombre debe tener entre 1 y 120 caracteres"
    if "descripcion" in data and (not isinstance(data["descripcion"], str) or len(data["descripcion"]) > 20000):
        return "descripcion debe ser texto de hasta 20000 caracteres"
    if "etapa" in data and (not isinstance(data["etapa"], str) or data["etapa"] not in Proyecto.ETAPAS):
        return "etapa no válida"
    for field in ("tecnologias", "lenguajes"):
        if field in data:
            values = data[field]
            if not isinstance(values, list):
                return f"{field} debe ser una lista"
            normalized = []
            seen_ids = set()
            for value in values:
                # Se aceptan IDs simples por compatibilidad; los nuevos clientes envían {id, nivel}.
                if type(value) is int:
                    item_id, level = value, "intermedio"
                elif isinstance(value, dict):
                    item_id, level = value.get("id"), value.get("nivel", "intermedio")
                else:
                    return f"Cada elemento de {field} debe incluir un ID válido"
                if type(item_id) is not int or item_id <= 0:
                    return f"Cada ID de {field} debe ser un entero positivo"
                if not isinstance(level, str) or level not in {"básico", "intermedio", "avanzado"}:
                    return "nivel debe ser básico, intermedio o avanzado"
                if item_id in seen_ids:
                    return f"No se permiten IDs duplicados en {field}"
                seen_ids.add(item_id)
                normalized.append({"id": item_id, "nivel": level})
            data[field] = normalized
    if "links" in data:
        if not isinstance(data["links"], list) or len(data["links"]) > 3:
            return "links debe ser una lista de hasta 3 enlaces"
        valid_types = {"demo", "github", "gitlab"}
        seen_types = set()
        for link in data["links"]:
            if not isinstance(link, dict) or not isinstance(link.get("tipo"), str) or link["tipo"] not in valid_types:
                return "Cada enlace debe tener tipo demo, github o gitlab"
            url = link.get("url")
            if not isinstance(url, str) or len(url) > 255:
                return "La URL debe ser texto de hasta 255 caracteres"
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
                return "Cada enlace debe ser una URL HTTP/HTTPS válida"
            if link["tipo"] in seen_types:
                return "No se permiten enlaces duplicados del mismo tipo"
            seen_types.add(link["tipo"])
    for field in ("fecha_inicio", "fecha_fin", "deadline"):
        if field in data and data[field] is not None:
            try:
                date.fromisoformat(data[field])
            except (ValueError, TypeError):
                return f"{field} debe tener formato YYYY-MM-DD"
    return None


@portfolio_bp.get("/proyectos")
@token_requerido
def listar_proyectos(usuario_id, user_role):
    try:
        return jsonify(Proyecto.listar_usuario(usuario_id)), 200
    except Exception:
        current_app.logger.exception("Error listando proyectos")
        return jsonify(error="No se pudieron cargar los proyectos"), 500


@portfolio_bp.post("/proyectos")
@token_requerido
def crear_proyecto(usuario_id, user_role):
    data = request.get_json(silent=True)
    error = _validar_payload(data, crear=True)
    if error:
        return jsonify(error=error), 400
    return _guardar_proyecto(usuario_id, data)


@portfolio_bp.route("/proyectos/<int:proyecto_id>", methods=["GET", "PUT", "DELETE"])
@token_requerido
def gestionar_proyecto(usuario_id, user_role, proyecto_id):
    if request.method == "GET":
        try:
            proyecto = Proyecto.obtener(usuario_id, proyecto_id)
            return (jsonify(proyecto), 200) if proyecto else (jsonify(error="Proyecto no encontrado"), 404)
        except Exception:
            current_app.logger.exception("Error consultando proyecto")
            return jsonify(error="No se pudo consultar el proyecto"), 500
    if request.method == "DELETE":
        try:
            deleted = Proyecto.eliminar(usuario_id, proyecto_id)
            return ("", 204) if deleted else (jsonify(error="Proyecto no encontrado"), 404)
        except Exception:
            current_app.logger.exception("Error eliminando proyecto")
            return jsonify(error="No se pudo eliminar el proyecto"), 500

    data = request.get_json(silent=True)
    error = _validar_payload(data)
    if error:
        return jsonify(error=error), 400
    if not data:
        return jsonify(error="No hay cambios para guardar"), 400
    return _guardar_proyecto(usuario_id, data, proyecto_id)


def _guardar_proyecto(usuario_id, data, proyecto_id=None):
    try:
        validar_ids_catalogo("tecnologias", [item["id"] for item in data.get("tecnologias", [])])
        validar_ids_catalogo("lenguajes", [item["id"] for item in data.get("lenguajes", [])])
        result_id = Proyecto.guardar(usuario_id, data, proyecto_id)
        return jsonify({"mensaje": "Proyecto guardado", "id": result_id}), 200 if proyecto_id else 201
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except LookupError:
        return jsonify(error="Proyecto no encontrado"), 404
    except CatalogUnavailable as exc:
        current_app.logger.warning("Validación de catálogo fallida: %s", exc)
        return jsonify(error=str(exc)), 503
    except Exception:
        current_app.logger.exception("Error guardando proyecto")
        return jsonify(error="No se pudo guardar el proyecto"), 500


@portfolio_bp.get("/perfil")
@token_requerido
def perfil_privado(usuario_id, user_role):
    from config.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, username, email, nombre_completo, bio FROM usuarios WHERE id=%s", (usuario_id,))
        user = cursor.fetchone()
        return (jsonify(user), 200) if user else (jsonify(error="Usuario no encontrado"), 404)
    finally:
        cursor.close()
        conn.close()
