from flask import Blueprint, jsonify
from services.auth import login as login_service
from flask import request
bp = Blueprint("auth", __name__)


@bp.post("/login")
def login():
    """Login a user."""
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        login_result = login_service(email, password)           
        if not login_result:
            return jsonify({"error": "Invalid email or password"}), 401
           
        return jsonify({
                "success": True, 
                "message": "Login successful", 
                "data": login_result
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.post("/register")
def register():
    """Register a new user."""
    return jsonify({"status": "ok"})

__all__ = ["bp"]