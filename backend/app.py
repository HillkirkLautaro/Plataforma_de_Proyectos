"""Entrada compatible para ejecutar el backend directamente."""

from backend import create_app

app = create_app()

if __name__ == "__main__":
    import os
    app.run(host=os.environ.get("FLASK_HOST", "0.0.0.0"),
            port=int(os.environ.get("FLASK_PORT", "5000")),
            debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
