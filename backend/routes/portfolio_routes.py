from datetime import date

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
    if "etapa" in data and data["etapa"] not in Proyecto.ETAPAS:
        return "etapa no válida"
    for field in ("tecnologias", "lenguajes"):
        if field in data:
            values = data[field]
            if not isinstance(values, list) or any(type(value) is not int or value <= 0 for value in values):
                return f"{field} debe ser una lista de IDs enteros positivos"
            data[field] = list(set(values))
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
        validar_ids_catalogo("tecnologias", data.get("tecnologias", []))
        validar_ids_catalogo("lenguajes", data.get("lenguajes", []))
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
