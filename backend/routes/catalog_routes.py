from dotenv import load_dotenv
from flask import Blueprint, jsonify, request
from werkzeug.exceptions import (
    BadGateway,
    GatewayTimeout,
    InternalServerError,
    TooManyRequests,
    Unauthorized,
)

from services.catalog_service import extraer_lista_catalogo, obtener_catalogo

load_dotenv()

catalog_bp = Blueprint("catalog_bp", __name__)


def _filtrar_por_nombre(datos, recurso: str, nombre_filtro: str):
    if not nombre_filtro:
        return datos
    lista = extraer_lista_catalogo(datos, recurso)
    return [
        item for item in lista
        if isinstance(item, dict) and nombre_filtro in str(item.get("nombre", "")).lower()
    ]


@catalog_bp.route("/lenguajes", methods=["GET"])
def get_lenguajes():
    try:
        nombre_filtro = request.args.get("nombre", "").strip().lower()
        datos = obtener_catalogo("lenguajes")
        return jsonify(_filtrar_por_nombre(datos, "lenguajes", nombre_filtro)), 200
    except (BadGateway, GatewayTimeout, Unauthorized, TooManyRequests, InternalServerError) as exc:
        return jsonify(error=exc.description), exc.code


@catalog_bp.route("/lenguajes/<int:lenguaje_id>", methods=["GET"])
def get_lenguaje_por_id(lenguaje_id):
    try:
        datos = obtener_catalogo("lenguajes")
        lista = extraer_lista_catalogo(datos, "lenguajes")
        encontrado = next((item for item in lista if isinstance(item, dict) and item.get("id") == lenguaje_id), None)
        if encontrado:
            return jsonify(encontrado), 200
        return jsonify({"error": "No encontramos el lenguaje solicitado."}), 404
    except (BadGateway, GatewayTimeout, Unauthorized, TooManyRequests, InternalServerError) as exc:
        return jsonify(error=exc.description), exc.code


@catalog_bp.route("/tecnologias", methods=["GET"])
def get_tecnologias():
    try:
        nombre_filtro = request.args.get("nombre", "").strip().lower()
        datos = obtener_catalogo("tecnologias")
        return jsonify(_filtrar_por_nombre(datos, "tecnologias", nombre_filtro)), 200
    except (BadGateway, GatewayTimeout, Unauthorized, TooManyRequests, InternalServerError) as exc:
        return jsonify(error=exc.description), exc.code


@catalog_bp.route("/tecnologias/<int:tecnologia_id>", methods=["GET"])
def get_tecnologia_por_id(tecnologia_id):
    try:
        datos = obtener_catalogo("tecnologias")
        lista = extraer_lista_catalogo(datos, "tecnologias")
        encontrado = next((item for item in lista if isinstance(item, dict) and item.get("id") == tecnologia_id), None)
        if encontrado:
            return jsonify(encontrado), 200
        return jsonify({"error": "No encontramos la tecnología solicitada."}), 404
    except (BadGateway, GatewayTimeout, Unauthorized, TooManyRequests, InternalServerError) as exc:
        return jsonify(error=exc.description), exc.code
