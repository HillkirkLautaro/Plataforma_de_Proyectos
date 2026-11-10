from datetime import datetime, timedelta, timezone
import re
import uuid

import jwt
from flask import Blueprint, current_app, request, jsonify
from mysql.connector import IntegrityError
from models.usuario import Usuario

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Se requiere un objeto JSON válido'}), 400
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if not all(isinstance(value, str) for value in (username, email, password)):
        return jsonify({'error': 'username, email y password son obligatorios'}), 400
    username, email, password = username.strip(), email.strip().lower(), password
    if not re.fullmatch(r'[A-Za-z0-9_.-]{3,50}', username):
        return jsonify({'error': 'El usuario debe tener 3-50 caracteres alfanuméricos, . _ o -'}), 400
    if len(email) > 100 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        return jsonify({'error': 'Correo electrónico inválido'}), 400
    if not 12 <= len(password) <= 72:
        return jsonify({'error': 'La contraseña debe tener entre 12 y 72 caracteres'}), 400
    nombre = data.get('nombre_completo', '')
    bio = data.get('bio', '')
    if not isinstance(nombre, str) or not isinstance(bio, str):
        return jsonify({'error': 'nombre_completo y bio deben ser texto'}), 400
    if len(nombre) > 100 or len(bio) > 10000:
        return jsonify({'error': 'Algún campo excede la longitud permitida'}), 400
    try:
        user_id = Usuario.crear(
            username,
            email,
            password,
            nombre.strip(),
            bio.strip()
        )
        return jsonify({'mensaje': 'Usuario registrado exitosamente', 'id': user_id}), 201
    except IntegrityError:
        return jsonify({'error': 'El usuario o correo ya está registrado'}), 409
    except Exception:
        current_app.logger.exception('Error al registrar usuario')
        return jsonify({'error': 'No se pudo completar el registro'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Se requiere un objeto JSON válido'}), 400
    identificador = data.get('username') or data.get('email')
    password = data.get('password')
    if not isinstance(identificador, str) or not isinstance(password, str) or not identificador or not password:
        return jsonify({'error': 'Credenciales requeridas'}), 400
        
    try:
        user = Usuario.obtener_por_credencial(identificador.strip().lower() if '@' in identificador else identificador.strip())
    except Exception:
        current_app.logger.exception('Error al consultar usuario para login')
        return jsonify({'error': 'No se pudo completar el inicio de sesión'}), 500
    if not user or not Usuario.verificar_password(user['password_hash'], password):
        return jsonify({'error': 'Credenciales incorrectas'}), 401
        
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
    return jsonify({'token': token, 'token_type': 'Bearer', 'expires_in': expires_minutes * 60,
                    'usuario': {'id': user['id'], 'username': user['username'], 'email': user['email'],
                                'nombre_completo': user.get('nombre_completo') or user['username']}}), 200
