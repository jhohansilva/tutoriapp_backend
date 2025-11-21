"""Authentication middleware for protecting routes."""
from functools import wraps
from flask import request, g
from services.auth import verify_token_and_get_user
from app.routes.response_utils import error_response


def require_auth(f):
    """
    Decorator to require authentication for a route.
    
    The token should be provided in the Authorization header as:
    Authorization: Bearer <token>
    
    After successful authentication, the user information is stored in g.current_user
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return error_response("Token de autenticación requerido", 401)
        
        # Extract token from "Bearer <token>" format
        try:
            token = auth_header.split(" ")[1]  # Get token after "Bearer "
        except IndexError:
            return error_response("Formato de token inválido. Use: Bearer <token>", 401)
        
        # Verify token and get user
        user = verify_token_and_get_user(token)
        
        if not user:
            return error_response("Token inválido o expirado", 401)
        
        # Store user in Flask's g object for use in the route
        g.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated_function

