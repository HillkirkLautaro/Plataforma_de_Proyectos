import os
import requests
from dotenv import load_dotenv
from flask import Blueprint, jsonify
from werkzeug.exceptions import BadGateway, GatewayTimeout, InternalServerError

load_dotenv()

catalog_bp = Blueprint('catalog_bp', __name__)


def _obtener_datos_profesor(recurso: str):
    """Consulta la API del docente o eleva las excepciones HTTP correspondientes."""
    profesor_url = os.environ.get('PROFESOR_API_URL')
    if not profesor_url:
        raise InternalServerError(description="La variable de entorno PROFESOR_API_URL no está configurada.")

    url = f"{profesor_url.rstrip('/')}/{recurso}"
    try:
        resp = requests.get(url, timeout=5)
        return resp.json(), resp.status_code
    except requests.exceptions.Timeout:
        raise GatewayTimeout(description="Tiempo de espera agotado al conectar con el servicio externo.")
    except requests.exceptions.RequestException:
        raise BadGateway(description="Error de comunicación con el servicio externo.")


@catalog_bp.route('/lenguajes', methods=['GET'])
def get_lenguajes():
    try:
            datos, status = _obtener_datos_profesor('lenguajes')
            return jsonify(datos), status
    except (BadGateway, GatewayTimeout):
            # Fallback local en caso de falla del upstream
            return jsonify([
                {"id": 1, "nombre": "Javascript"},
                {"id": 2, "nombre": "MySQL", "categoria": "base de datos"}
            ]), 200


@catalog_bp.route('/tecnologias', methods=['GET'])
def get_tecnologias():
    try:
        datos, status = _obtener_datos_profesor('tecnologias')
        return jsonify(datos), status
    except (BadGateway, GatewayTimeout):
        # Fallback local en caso de falla del upstream
        return jsonify([
            {"id": 1, "nombre": "Flask", "categoria": "framework"},
            {"id": 2, "nombre": "MySQL", "categoria": "base de datos"}
        ]), 200