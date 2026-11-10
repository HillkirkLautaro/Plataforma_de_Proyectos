import jwt
from functools import wraps
from flask import request, jsonify, current_app

def token_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith("Bearer "):
            parts = auth_header.split()
            if len(parts) == 2:
                token = parts[1]
            
        if not token:
            return jsonify({'error': 'Token de autenticación faltante'}), 401
            
        try:
            data = jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=["HS256"],
                              issuer=current_app.config['JWT_ISSUER'],
                              options={"require": ["sub", "exp", "iat", "iss", "jti"]})
            usuario_id = int(data['sub'])
            user_role = data.get('rol', 'usuario')
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'El token ha expirado'}), 401
        except (jwt.InvalidTokenError, ValueError, TypeError):
            return jsonify({'error': 'Token inválido'}), 401
            
        return f(usuario_id=usuario_id, user_role=user_role, *args, **kwargs)
    return decorated
