from flask import Flask
from flask_cors import CORS


def create_app() -> Flask:
    """Application factory for the Tutoriapp backend."""
    app = Flask(__name__)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from app.routes import init_app as init_routes

    init_routes(app)

    return app


__all__ = ["create_app"]

