from flask import Blueprint, current_app, jsonify, request
from middlewares.auth_middleware import token_requerido
from models.habilidad import Habilidad, HabilidadDuplicadaError
from models.proyecto import Proyecto
from models.usuario import Usuario
from services.catalog_service import CatalogUnavailable, validar_ids_catalogo
from services.schema_validator import validar_schema

portfolio_bp = Blueprint("portfolio_bp", __name__)

_MAPA_TIPOS_HABILIDAD = {
    "tecnologia": "tecnologia",
    "tecnologias": "tecnologia",
    "lenguaje": "lenguaje",
    "lenguajes": "lenguaje",
}


def _normalizar_tipo_habilidad(tipo: str) -> str | None:
    return _MAPA_TIPOS_HABILIDAD.get(tipo.strip().lower())


def _validar_y_normalizar_payload_proyecto(data, completo: bool = False):
    if isinstance(data, dict):
        data = dict(data)
        if isinstance(data.get("nombre"), str):
            data["nombre"] = data["nombre"].strip()

    schema = Proyecto.SCHEMAS["proyecto_crear"] if completo else Proyecto.SCHEMAS["proyecto"]
    error_schema = validar_schema(data, schema)
    if error_schema:
        return None, error_schema

    etiquetas_duplicados = {
        "tecnologias": "No puedes seleccionar la misma tecnología más de una vez.",
        "lenguajes": "No puedes seleccionar el mismo lenguaje más de una vez.",
    }
    for field in ("tecnologias", "lenguajes"):
        if field in data:
            normalized = []
            seen_ids = set()
            for value in data[field]:
                item = {"id": value, "nivel": "intermedio"} if isinstance(value, int) else {
                    "id": value["id"],
                    "nivel": value.get("nivel", "intermedio"),
                }
                if item["id"] in seen_ids:
                    return None, etiquetas_duplicados[field]
                seen_ids.add(item["id"])
                normalized.append(item)
            data[field] = normalized

    if "links" in data:
        seen_types = set()
        for link in data["links"]:
            if link["tipo"] in seen_types:
                return None, "No puedes agregar más de un enlace del mismo tipo."
            seen_types.add(link["tipo"])

    return data, None


def _persistir_proyecto(usuario_id: int, data: dict, proyecto_id: int | None = None):
    try:
        proyecto_actual = None
        if proyecto_id is not None:
            proyecto_actual = Proyecto.obtener(usuario_id, proyecto_id)
            if proyecto_actual is None:
                raise LookupError("Proyecto inexistente")

        Proyecto.validar_reglas_negocio(data, proyecto_actual=proyecto_actual, crear=(proyecto_id is None))
        validar_ids_catalogo("tecnologias", [item["id"] for item in data.get("tecnologias", [])])
        validar_ids_catalogo("lenguajes", [item["id"] for item in data.get("lenguajes", [])])
        result_id = Proyecto.guardar(usuario_id, data, proyecto_id)
        proyecto_guardado = Proyecto.obtener(usuario_id, result_id)
        mensaje = "Proyecto actualizado correctamente." if proyecto_id else "Proyecto creado correctamente."
        return jsonify({
            "mensaje": mensaje,
            "id": result_id,
            "proyecto": proyecto_guardado,
        }), 200 if proyecto_id else 201
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except LookupError:
        return jsonify(error="No encontramos el proyecto que intentas actualizar."), 404
    except CatalogUnavailable as exc:
        current_app.logger.warning("Validación de catálogo fallida: %s", exc)
        return jsonify(error=str(exc)), 503
    except Exception:
        current_app.logger.exception("Error guardando proyecto")
        return jsonify(error="No pudimos guardar el proyecto en este momento. Intenta nuevamente más tarde."), 500


def _normalizar_payload_perfil(raw_data):
    if not isinstance(raw_data, dict):
        return raw_data
    data = dict(raw_data)
    if isinstance(data.get("nombre_completo"), str):
        data["nombre_completo"] = data["nombre_completo"].strip()
    if isinstance(data.get("bio"), str):
        data["bio"] = data["bio"].strip()
    return data


def _actualizar_perfil_con_schema(usuario_id: int, schema: dict):
    data = _normalizar_payload_perfil(request.get_json(silent=True))
    error_schema = validar_schema(data, schema)
    if error_schema:
        return jsonify(error=error_schema), 400

    try:
        perfil = Usuario.actualizar_perfil(usuario_id, data)
        if not perfil:
            return jsonify(error="No encontramos tu perfil de usuario."), 404
        return jsonify({"mensaje": "Perfil actualizado correctamente.", "perfil": perfil}), 200
    except Exception:
        current_app.logger.exception("Error actualizando perfil de usuario")
        return jsonify(error="No pudimos actualizar tu perfil en este momento. Intenta nuevamente más tarde."), 500


# ==========================================================================
# Proyectos del usuario autenticado
# ==========================================================================

@portfolio_bp.get("/proyectos")
@token_requerido
def listar_proyectos(usuario_id, user_role):
    try:
        return jsonify(Proyecto.listar_usuario(usuario_id)), 200
    except Exception:
        current_app.logger.exception("Error listando proyectos")
        return jsonify(error="No pudimos cargar tus proyectos en este momento. Intenta nuevamente más tarde."), 500


@portfolio_bp.post("/proyectos")
@token_requerido
def crear_proyecto(usuario_id, user_role):
    data, error = _validar_y_normalizar_payload_proyecto(request.get_json(silent=True), completo=True)
    if error:
        return jsonify(error=error), 400
    return _persistir_proyecto(usuario_id, data)


@portfolio_bp.get("/proyectos/<int:proyecto_id>")
@token_requerido
def obtener_proyecto(usuario_id, user_role, proyecto_id):
    try:
        proyecto = Proyecto.obtener(usuario_id, proyecto_id)
        if not proyecto:
            return jsonify(error="No encontramos el proyecto solicitado."), 404
        return jsonify(proyecto), 200
    except Exception:
        current_app.logger.exception("Error consultando proyecto")
        return jsonify(error="No pudimos cargar el proyecto en este momento. Intenta nuevamente más tarde."), 500


@portfolio_bp.put("/proyectos/<int:proyecto_id>")
@token_requerido
def reemplazar_proyecto(usuario_id, user_role, proyecto_id):
    data, error = _validar_y_normalizar_payload_proyecto(request.get_json(silent=True), completo=True)
    if error:
        return jsonify(error=error), 400
    return _persistir_proyecto(usuario_id, data, proyecto_id)


@portfolio_bp.patch("/proyectos/<int:proyecto_id>")
@token_requerido
def actualizar_proyecto(usuario_id, user_role, proyecto_id):
    data, error = _validar_y_normalizar_payload_proyecto(request.get_json(silent=True), completo=False)
    if error:
        return jsonify(error=error), 400
    return _persistir_proyecto(usuario_id, data, proyecto_id)


@portfolio_bp.delete("/proyectos/<int:proyecto_id>")
@token_requerido
def eliminar_proyecto(usuario_id, user_role, proyecto_id):
    try:
        deleted = Proyecto.eliminar(usuario_id, proyecto_id)
        if not deleted:
            return jsonify(error="No encontramos el proyecto que intentas eliminar."), 404
        return jsonify(mensaje="Proyecto eliminado correctamente.", accion="Proyecto eliminado"), 200
    except Exception:
        current_app.logger.exception("Error eliminando proyecto")
        return jsonify(error="No pudimos eliminar el proyecto en este momento. Intenta nuevamente más tarde."), 500


# ==========================================================================
# Perfil del usuario autenticado
# ==========================================================================

@portfolio_bp.get("/perfil")
@token_requerido
def obtener_perfil(usuario_id, user_role):
    try:
        user = Usuario.obtener_perfil_privado(usuario_id)
        if not user:
            return jsonify(error="No encontramos tu perfil de usuario."), 404
        habilidades = Habilidad.listar_usuario(usuario_id)
        return jsonify({
            **user,
            "habilidades": habilidades["tecnologias"],
            "lenguajes": habilidades["lenguajes"],
        }), 200
    except Exception:
        current_app.logger.exception("Error consultando perfil privado")
        return jsonify(error="No pudimos cargar tu perfil en este momento. Intenta nuevamente más tarde."), 500


@portfolio_bp.put("/perfil")
@token_requerido
def reemplazar_perfil(usuario_id, user_role):
    return _actualizar_perfil_con_schema(usuario_id, Usuario.SCHEMA_PERFIL_PUT)


@portfolio_bp.patch("/perfil")
@token_requerido
def actualizar_perfil(usuario_id, user_role):
    return _actualizar_perfil_con_schema(usuario_id, Usuario.SCHEMA_PERFIL_PATCH)


# ==========================================================================
# Habilidades del perfil (tecnologías y lenguajes)
# ==========================================================================

@portfolio_bp.post("/perfil/habilidades")
@token_requerido
def crear_habilidad_perfil(usuario_id, user_role):
    raw_data = request.get_json(silent=True)
    error_schema = validar_schema(raw_data, Habilidad.SCHEMA_CREAR)
    if error_schema:
        return jsonify(error=error_schema), 400

    tipo = raw_data["tipo"]
    item_id = raw_data["id"]
    nivel = raw_data["nivel"]
    recurso_catalogo = "tecnologias" if tipo == "tecnologia" else "lenguajes"

    try:
        validar_ids_catalogo(recurso_catalogo, [item_id])
        Habilidad.crear(usuario_id, tipo, item_id, nivel)
        return jsonify({
            "mensaje": "Habilidad agregada correctamente.",
            "habilidad": {"tipo": tipo, "id": item_id, "nivel": nivel},
        }), 201
    except HabilidadDuplicadaError:
        return jsonify(error="La habilidad ya existe en el perfil."), 409
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except CatalogUnavailable as exc:
        current_app.logger.warning("Validación de catálogo fallida al crear habilidad: %s", exc)
        return jsonify(error=str(exc)), 503
    except Exception:
        current_app.logger.exception("Error creando habilidad del perfil")
        return jsonify(error="No pudimos agregar la habilidad en este momento. Intenta nuevamente más tarde."), 500


@portfolio_bp.put("/perfil/habilidades/<string:tipo>/<int:item_id>")
@token_requerido
def actualizar_habilidad_perfil(usuario_id, user_role, tipo, item_id):
    tipo_normalizado = _normalizar_tipo_habilidad(tipo)
    if not tipo_normalizado:
        return jsonify(error="El tipo de habilidad indicado no es válido."), 400
    if item_id < 1:
        return jsonify(error="El campo 'identificador' debe ser mayor o igual a 1."), 400

    raw_data = request.get_json(silent=True)
    error_schema = validar_schema(raw_data, Habilidad.SCHEMA_ACTUALIZAR)
    if error_schema:
        return jsonify(error=error_schema), 400

    nivel = raw_data["nivel"]
    recurso_catalogo = "tecnologias" if tipo_normalizado == "tecnologia" else "lenguajes"

    try:
        validar_ids_catalogo(recurso_catalogo, [item_id])
        actualizada = Habilidad.actualizar_nivel(usuario_id, tipo_normalizado, item_id, nivel)
        if not actualizada:
            return jsonify(error="La habilidad no se encuentra en el perfil."), 404
        return jsonify({
            "mensaje": "Nivel de habilidad actualizado correctamente.",
            "habilidad": {"tipo": tipo_normalizado, "id": item_id, "nivel": nivel},
        }), 200
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except CatalogUnavailable as exc:
        current_app.logger.warning("Validación de catálogo fallida al actualizar habilidad: %s", exc)
        return jsonify(error=str(exc)), 503
    except Exception:
        current_app.logger.exception("Error actualizando habilidad del perfil")
        return jsonify(error="No pudimos actualizar la habilidad en este momento. Intenta nuevamente más tarde."), 500


@portfolio_bp.delete("/perfil/habilidades/<string:tipo>/<int:item_id>")
@token_requerido
def eliminar_habilidad_perfil(usuario_id, user_role, tipo, item_id):
    tipo_normalizado = _normalizar_tipo_habilidad(tipo)
    if not tipo_normalizado:
        return jsonify(error="El tipo de habilidad indicado no es válido."), 400

    try:
        eliminada = Habilidad.eliminar(usuario_id, tipo_normalizado, item_id)
        if not eliminada:
            return jsonify(error="No encontramos la habilidad que intentas eliminar."), 404
        return jsonify({"mensaje": "Habilidad eliminada correctamente."}), 200
    except Exception:
        current_app.logger.exception("Error eliminando habilidad del perfil")
        return jsonify(error="No pudimos eliminar la habilidad en este momento. Intenta nuevamente más tarde."), 500
