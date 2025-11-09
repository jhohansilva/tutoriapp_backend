from flask import Flask


def create_app() -> Flask:
    """Application factory for the Tutoriapp backend."""
    app = Flask(__name__)

    from app.routes import init_app as init_routes

    init_routes(app)

    return app


__all__ = ["create_app"]

