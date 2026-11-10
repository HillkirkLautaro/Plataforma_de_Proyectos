import os
import requests
from dotenv import load_dotenv
from cachetools import TTLCache
from flask import Blueprint, jsonify
from werkzeug.exceptions import BadGateway, GatewayTimeout, InternalServerError

load_dotenv()

catalog_bp = Blueprint('catalog_bp', __name__)

cache = TTLCache(maxsize=10, ttl=3600)

def _obtener_datos_profesor(recurso: str):
    """Consulta la API del docente incluyendo el encabezado de autenticación."""
    profesor_url = os.environ.get('PROFESOR_API_URL')
    access_key = os.environ.get('GRUPO_ACCESS_KEY')

    if not profesor_url:
        raise InternalServerError(description="La variable de entorno PROFESOR_API_URL no está configurada.")
    
    if not access_key:
        raise InternalServerError(description="La variable de entorno GRUPO_ACCESS_KEY no está configurada.")

    # Encabezados enviados hacia el servicio externo
    headers = {
        'Grupo-Access-Key': access_key,
        'Content-Type': 'application/json'
    }

    url = f"{profesor_url.rstrip('/')}/{recurso}"
    try:
        resp = requests.get(url, headers=headers, timeout=5)

        if resp.status_code == 401:
            raise Unauthorized(description="Grupo-Access-Key no autorizada o vencida.")

        if resp.status_code == 200:
            datos = resp.json()
            cache[recurso] = datos  # Guardar en caché solo si la respuesta fue exitosa
            return datos, 200

        return resp.json(), resp.status_code
        
        # Si la API externa rechaza la clave por credencial inválida
        if resp.status_code == 401:
            raise Unauthorized(description="GRUPO-ACCESS-KEY no autorizada o vencida.")
            
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