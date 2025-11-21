from flask import Blueprint

from app.routes.response_utils import success_response

bp = Blueprint("health", __name__)


@bp.get("/")
def api_index():
    """Root endpoint for the API namespace."""
    return success_response({}, "API está funcionando correctamente")


@bp.get("/health")
def health_check():
    """Lightweight endpoint to verify the service is running."""
    return success_response({}, "Servicio funcionando correctamente", 200)


__all__ = ["bp"]

