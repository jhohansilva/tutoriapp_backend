from flask import Flask


def create_app() -> Flask:
    """Application factory for the Tutoriapp backend."""
    app = Flask(__name__)

    from .routes import api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    return app


__all__ = ["create_app"]

