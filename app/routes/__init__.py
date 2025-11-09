from flask import Flask


def init_app(app: Flask) -> None:
    """Register all route blueprints on the given Flask app."""
    from app.routes import health
    from app.routes import auth

    app.register_blueprint(health.bp, url_prefix="/api")
    app.register_blueprint(auth.bp, url_prefix="/api")


__all__ = ["init_app"]

