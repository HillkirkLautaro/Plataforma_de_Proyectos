from flask import Blueprint, jsonify, current_app
from config.db import get_db_connection
from models.proyecto import Proyecto

public_bp = Blueprint("public_bp", __name__)


@public_bp.route("/portafolio/<int:usuario_id>", methods=["GET"])
def ver_portafolio(usuario_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, username, nombre_completo, bio FROM usuarios WHERE id=%s", (usuario_id,))
        perfil = cursor.fetchone()
        if not perfil:
            return jsonify(error="Desarrollador no encontrado"), 404
        cursor.execute("SELECT tecnologia_id, nivel FROM usuario_habilidades WHERE usuario_id=%s", (usuario_id,))
        habilidades = cursor.fetchall()
        proyectos = Proyecto.listar_usuario(usuario_id)
        return jsonify(perfil=perfil, habilidades=habilidades, proyectos=proyectos), 200
    except Exception:
        current_app.logger.exception("Error cargando portfolio público")
        return jsonify(error="No se pudo cargar el portfolio"), 500
    finally:
        cursor.close()
        conn.close()
