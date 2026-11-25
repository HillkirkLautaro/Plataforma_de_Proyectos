from flask import Blueprint, jsonify, current_app
from models.proyecto import Proyecto
from models.usuario import Usuario

public_bp = Blueprint("public_bp", __name__)


@public_bp.get("/desarrolladores")
def listar_desarrolladores():
    """Directorio público; no incluye correos ni información de autenticación."""
    try:
        desarrolladores = Usuario.listar_publicos()
        return jsonify(desarrolladores), 200
    except Exception:
        current_app.logger.exception("Error listando portfolios públicos")
        return jsonify(error="No pudimos cargar el listado de desarrolladores en este momento. Intenta nuevamente más tarde."), 500


@public_bp.get("/portafolio/<int:usuario_id>")
def ver_portafolio(usuario_id):
    try:
        datos_usuario = Usuario.obtener_portafolio_publico(usuario_id)

        if not datos_usuario:
            return jsonify({"error": "No encontramos el portafolio del desarrollador solicitado."}), 404

        proyectos = Proyecto.listar_usuario(usuario_id)

        return jsonify({
            "perfil": datos_usuario["perfil"],
            "habilidades": datos_usuario["habilidades"],
            "lenguajes": datos_usuario["lenguajes"],
            "proyectos": proyectos
        }), 200

    except Exception:
        current_app.logger.exception("Error cargando portfolio público")
        return jsonify({
            "error": "No pudimos cargar este portafolio en este momento. Intenta nuevamente más tarde."
        }), 500