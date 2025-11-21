from flask import Blueprint, request, g

from services.auth import login as login_service, change_password as change_password_service
from app.routes.response_utils import success_response, error_response
from app.middleware import require_auth

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


@bp.post("/change-password")
@require_auth
def change_password():
    """Change password for authenticated user."""
    try:
        # Acceder a la información del usuario autenticado
        current_user = g.current_user
        user_id = current_user["id"]
        
        data = request.get_json()
        old_password = data.get("old_password")
        new_password = data.get("new_password")
        
        if not old_password or not new_password:
            return error_response("old_password and new_password are required", 400)
        
        # Validar que la nueva contraseña tenga al menos cierta longitud
        if len(new_password) < 6:
            return error_response("New password must be at least 6 characters long", 400)
        
        # Cambiar la contraseña
        result = change_password_service(user_id, old_password, new_password)
        
        if not result:
            return error_response("Invalid old password or user not found", 401)
        
        return success_response(result, "Contraseña cambiada exitosamente", 200)
        
    except Exception as e:
        return error_response(str(e), 500)


__all__ = ["bp"]