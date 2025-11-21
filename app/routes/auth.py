from flask import Blueprint, request

from services.auth import login as login_service
from app.routes.response_utils import success_response, error_response

bp = Blueprint("auth", __name__)


@bp.post("/login")
def login():
    """Login a user."""
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        if not email or not password:
            return error_response("Email and password are required", 400)

        login_result = login_service(email, password)           
        if not login_result:
            return error_response("Invalid email or password", 401)
           
        return success_response(login_result, "Login successful", 200)

    except Exception as e:
        return error_response(str(e), 500)

@bp.post("/register")
def register():
    """Register a new user."""
    return success_response({}, "Registro exitoso", 200)

__all__ = ["bp"]