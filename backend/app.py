import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from routes.catalog_routes import catalog_bp

def create_app():
    # Ruta absoluta a la carpeta frontend
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

    app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
    CORS(app)


    app.register_blueprint(catalog_bp, url_prefix='/api/catalogo')

    # Ruta raíz para servir index.html
    @app.route('/')
    def serve_frontend():
        return send_from_directory(frontend_dir, 'index.html')
        

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
