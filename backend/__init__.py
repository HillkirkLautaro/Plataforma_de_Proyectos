"""Aplicación Flask y configuración de rutas del backend."""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS


def create_app():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(backend_dir)
    load_dotenv(os.path.join(project_dir, ".env"))
    # Compatibilidad con la configuración existente, nunca sobreescribe el .env raíz.
    load_dotenv(os.path.join(backend_dir, ".env"))

    secret = os.environ.get("JWT_SECRET") or os.environ.get("SECRET_KEY")
    if not secret or len(secret) < 32:
        raise RuntimeError("Definí JWT_SECRET (o SECRET_KEY) con al menos 32 caracteres en .env")

    frontend_dir = os.path.join(project_dir, "frontend")
    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    app.config.update(
        JWT_SECRET=secret,
        JWT_ISSUER=os.environ.get("JWT_ISSUER", "portfolio-api"),
        JWT_EXP_MINUTES=int(os.environ.get("JWT_EXP_MINUTES", "30")),
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    origins = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "").split(",") if origin.strip()]
    # La misma aplicación sirve el frontend; solo abrir CORS cross-origin si se configura explícitamente.
    CORS(app, origins=origins, allow_headers=["Content-Type", "Authorization"])

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

    @app.route("/")
    def serve_frontend():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/dashboard")
    def serve_dashboard():
        return send_from_directory(os.path.join(frontend_dir, "views"), "dashboard.html")

    @app.route("/portfolios/<int:usuario_id>")
    def serve_public_portfolio(usuario_id):
        return send_from_directory(os.path.join(frontend_dir, "views"), "portfolio.html")

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify(error="El cuerpo de la solicitud excede el límite permitido"), 413

    return app
