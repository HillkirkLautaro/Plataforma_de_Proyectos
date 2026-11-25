from datetime import datetime, timedelta, timezone
import uuid

import jwt
from flask import Blueprint, current_app, request, jsonify
from mysql.connector import IntegrityError
from models.usuario import Usuario
from services.schema_validator import validar_schema

auth_bp = Blueprint('auth_bp', __name__)


def _hay_sesion_activa():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return False
    try:
        parts = auth_header.split()
        if len(parts) != 2:
            return False
        jwt.decode(
            parts[1], current_app.config['JWT_SECRET'], algorithms=['HS256'],
            issuer=current_app.config['JWT_ISSUER'],
            options={'require': ['sub', 'exp', 'iat', 'iss', 'jti']},
        )
        return True
    except jwt.InvalidTokenError:
        return False


def _generar_respuesta_sesion(user, mensaje):
    now = datetime.now(timezone.utc)
    expires_minutes = current_app.config['JWT_EXP_MINUTES']
    payload = {
        'sub': str(user['id']),
        'username': user['username'],
        'rol': user.get('rol', 'usuario'),
        'iss': current_app.config['JWT_ISSUER'],
        'iat': now,
        'exp': now + timedelta(minutes=expires_minutes),
        'jti': uuid.uuid4().hex,
    }
    token = jwt.encode(payload, current_app.config['JWT_SECRET'], algorithm='HS256')
    return {
        'mensaje': mensaje,
        'token': token,
        'token_type': 'Bearer',
        'expires_in': expires_minutes * 60,
        'usuario': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'nombre_completo': user.get('nombre_completo') or user['username'],
        },
    }


@auth_bp.route('/register', methods=['POST'])
def register():
    if _hay_sesion_activa():
        return jsonify({'error': 'Ya tienes una sesión iniciada.', 'redirect': '/dashboard'}), 409

    data = request.get_json(silent=True)

    if isinstance(data, dict):
        data = dict(data)
        if isinstance(data.get('username'), str):
            data['username'] = data['username'].strip()
        if isinstance(data.get('email'), str):
            data['email'] = data['email'].strip().lower()
        if isinstance(data.get('nombre_completo'), str):
            data['nombre_completo'] = data['nombre_completo'].strip()
        if isinstance(data.get('bio'), str):
            data['bio'] = data['bio'].strip()

    error_schema = validar_schema(data, Usuario.SCHEMA_REGISTRO)
    if error_schema:
        return jsonify({'error': error_schema}), 400

    try:
        user_id = Usuario.crear(
            data['username'],
            data['email'],
            data['password'],
            data.get('nombre_completo', ''),
            data.get('bio', '')
        )
    except IntegrityError:
        return jsonify({'error': 'El nombre de usuario o el correo electrónico ya se encuentran registrados.'}), 409
    except Exception:
        current_app.logger.exception('Error al registrar usuario')
        return jsonify({'error': 'No pudimos completar tu registro en este momento. Intenta nuevamente más tarde.'}), 500

    nuevo_usuario = {
        'id': user_id,
        'username': data['username'],
        'email': data['email'],
        'nombre_completo': data.get('nombre_completo') or data['username'],
        'rol': 'usuario',
    }
    try:
        respuesta = _generar_respuesta_sesion(nuevo_usuario, 'Usuario registrado exitosamente.')
        respuesta['id'] = user_id
        return jsonify(respuesta), 201
    except Exception:
        current_app.logger.exception('Usuario %s registrado, pero falló la generación del token JWT', user_id)
        return jsonify({
            'mensaje': 'Tu cuenta fue creada exitosamente, pero no pudimos iniciar tu sesión automáticamente. Por favor, inicia sesión manualmente.',
            'id': user_id,
            'usuario': {
                'id': user_id,
                'username': nuevo_usuario['username'],
                'email': nuevo_usuario['email'],
                'nombre_completo': nuevo_usuario['nombre_completo'],
            },
        }), 201
    
@auth_bp.route('/login', methods=['POST'])
def login():
    # No emitir una segunda sesión cuando el cliente ya presenta un JWT vigente.
    if _hay_sesion_activa():
        return jsonify({'error': 'Ya tienes una sesión iniciada.', 'redirect': '/dashboard'}), 409

    data = request.get_json(silent=True)

    if isinstance(data, dict):
        data = dict(data)
        if isinstance(data.get('username'), str):
            data['username'] = data['username'].strip()
        if isinstance(data.get('email'), str):
            data['email'] = data['email'].strip().lower()

    error_schema = validar_schema(data, Usuario.SCHEMA_LOGIN)
    if error_schema:
        return jsonify({'error': error_schema}), 400

    identificador = data.get('username') or data.get('email')
    password = data['password']

    try:
        user = Usuario.obtener_por_credencial(identificador)
    except Exception:
        current_app.logger.exception('Error al consultar usuario para login')
        return jsonify({'error': 'No pudimos iniciar tu sesión en este momento. Intenta nuevamente más tarde.'}), 500

    if not user or not Usuario.verificar_password(user['password_hash'], password):
        return jsonify({'error': 'El usuario o la contraseña son incorrectos.'}), 401

    return jsonify(_generar_respuesta_sesion(user, 'Inicio de sesión exitoso.')), 200