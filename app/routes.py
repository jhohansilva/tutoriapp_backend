from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__)


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Lightweight endpoint to verify the service is running."""
    return jsonify({"status": "ok"}), 200

