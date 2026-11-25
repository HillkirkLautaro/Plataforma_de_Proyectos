"""Aplicación Flask y configuración de rutas del backend."""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException


DEFAULT_CORS_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:5000",
    "http://localhost:5000",
]


def create_app():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(backend_dir)
    load_dotenv(os.path.join(project_dir, ".env"))
    # Compatibilidad con la configuración existente, nunca sobreescribe el .env raíz.
    load_dotenv(os.path.join(backend_dir, ".env"))

    secret = os.environ.get("JWT_SECRET") or os.environ.get("SECRET_KEY")
    if not secret or len(secret) < 32:
        raise RuntimeError("Definí JWT_SECRET (o SECRET_KEY) con al menos 32 caracteres en .env")

    # El backend expone únicamente endpoints HTTP; el frontend se despliega por separado.
    app = Flask(__name__, static_folder=None)
    app.config.update(
        JWT_SECRET=secret,
        JWT_ISSUER=os.environ.get("JWT_ISSUER", "portfolio-api"),
        JWT_EXP_MINUTES=int(os.environ.get("JWT_EXP_MINUTES", "30")),
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    raw_origins = os.environ.get("CORS_ORIGINS", "")
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()] or DEFAULT_CORS_ORIGINS
    CORS(
        app,
        resources={r"/*": {"origins": origins}},
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    # Las rutas antiguas usan imports absolutos desde backend/.
    import sys
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from routes.catalog_routes import catalog_bp
    from routes.auth_routes import auth_bp
    from routes.public_routes import public_bp
    from routes.portfolio_routes import portfolio_bp

    app.register_blueprint(catalog_bp, url_prefix="/api/catalogo")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(public_bp, url_prefix="/api")
    app.register_blueprint(portfolio_bp, url_prefix="/api/portfolio")

    @app.errorhandler(400)
    def bad_request(_error):
        return jsonify(error="La solicitud enviada no es válida. Revisa los datos e intenta nuevamente."), 400

    @app.errorhandler(401)
    def unauthorized(_error):
        return jsonify(error="Debes iniciar sesión para acceder a esta sección."), 401

    @app.errorhandler(403)
    def forbidden(_error):
        return jsonify(error="No tienes permisos para realizar esta acción."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error="El recurso solicitado no existe."), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify(error="La acción solicitada no está permitida para esta dirección."), 405

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify(error="Los datos enviados superan el tamaño máximo permitido."), 413

    @app.errorhandler(429)
    def too_many_requests(_error):
        return jsonify(error="Has realizado demasiadas solicitudes. Espera unos minutos e intenta nuevamente."), 429

    @app.errorhandler(500)
    def internal_server_error(_error):
        app.logger.exception("Error interno del servidor")
        return jsonify(error="Ocurrió un error inesperado en el servidor. Intenta nuevamente en unos minutos."), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        code = error.code or 500
        if code >= 500:
            app.logger.exception("Excepción HTTP %s no controlada", code)
            return jsonify(error="Ocurrió un error inesperado en el servidor. Intenta nuevamente en unos minutos."), code
        return jsonify(error="No se pudo procesar tu solicitud. Revisa los datos e intenta nuevamente."), code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(_error):
        app.logger.exception("Error inesperado no controlado")
        return jsonify(error="Ocurrió un error inesperado en el servidor. Intenta nuevamente en unos minutos."), 500

    return app
