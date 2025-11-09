from flask import Blueprint, jsonify

bp = Blueprint("health", __name__)


@bp.get("/")
def api_index():
    """Root endpoint for the API namespace."""
    return jsonify({"status": "ok"})


@bp.get("/health")
def health_check():
    """Lightweight endpoint to verify the service is running."""
    return jsonify({"status": "ok"}), 200


__all__ = ["bp"]

