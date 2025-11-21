"""Utility functions for standardizing API responses."""
from flask import jsonify
from typing import Any, Optional, Dict


def success_response(data: Any, message: str = "Operación exitosa", code: int = 200) -> tuple:
    """
    Create a standardized success response.
    
    Args:
        data: The data to include in the response
        message: Optional success message
        code: HTTP status code (default: 200)
    
    Returns:
        Tuple of (jsonify response, status_code)
    """
    response = {
        "success": True,
        "code": code,
        "message": message,
        "data": data
    }
    return jsonify(response), code


def error_response(message: str, code: int = 400) -> tuple:
    """
    Create a standardized error response.
    
    Args:
        message: Error message
        code: HTTP status code (default: 400)
    
    Returns:
        Tuple of (jsonify response, status_code)
    """
    response = {
        "success": False,
        "code": code,
        "message": message
    }
    return jsonify(response), code

