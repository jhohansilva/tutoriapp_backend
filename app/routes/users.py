from flask import Blueprint, jsonify, request

from services import users as users_service

bp = Blueprint("users", __name__)

VALID_ROLES = {"admin", "user"}
VALID_SESSION_STUDENT_STATUSES = {"requested", "registered", "absent", "attended", "rejected"}

@bp.get("/users")
def list_users():
    role = request.args.get("role")
    status_param = request.args.get("status")
    search = request.args.get("search")

    if role and role not in VALID_ROLES:
        return (
            jsonify(
                {
                    "error": "Invalid role value",
                    "allowed": list(VALID_ROLES),
                }
            ),
            400,
        )

    status = None
    if status_param is not None:
        if status_param.lower() in {"true", "1"}:
            status = True
        elif status_param.lower() in {"false", "0"}:
            status = False
        else:
            return (
                jsonify(
                    {
                        "error": "Invalid status value, expected 'true' or 'false'",
                    }
                ),
                400,
            )

    users = users_service.find_many(role=role, status=status, search=search)
    return jsonify({"data": users})


@bp.get("/users/<int:user_id>")
def get_user(user_id: int):
    user = users_service.find_one(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"data": user})


@bp.post("/users")
def create_user():
    payload = request.get_json(silent=True) or {}

    required_fields = {"email", "password", "name"}
    missing = [field for field in required_fields if field not in payload]
    if missing:
        return (
            jsonify({"error": "Missing required fields", "required": missing}),
            400,
        )

    user_data = {
        "email": payload["email"],
        "password": payload["password"],
        "name": payload["name"],
    }

    optional_fields = {
        "role",
        "second_name",
        "second_surname",
        "phone_number",
        "status",
    }
    for field in optional_fields:
        if field in payload and payload[field] is not None:
            user_data[field] = payload[field]

    role = user_data.get("role")
    if role and role not in VALID_ROLES:
        return (
            jsonify(
                {"error": "Invalid role value", "allowed": list(VALID_ROLES)}
            ),
            400,
        )

    try:
        user = users_service.create_user(user_data)
        return jsonify({"data": user}), 201
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.put("/users/<int:user_id>")
def update_user(user_id: int):
    payload = request.get_json(silent=True) or {}
    
    if not payload:
        return jsonify({"error": "No data provided"}), 400

    updatable_fields = {
        "email",
        "password",
        "name",
        "phone_number",
        "role",
    }
    
    user_data = {}
    for field in updatable_fields:
        if field in payload and payload[field] is not None:
            user_data[field] = payload[field]

    if "role" in user_data and user_data["role"] not in VALID_ROLES:
        return (
            jsonify(
                {"error": "Invalid role value", "allowed": list(VALID_ROLES)}
            ),
            400,
        )

    if not user_data:
        return jsonify({"error": "No valid fields to update"}), 400

    try:
        user = users_service.update_user(user_id, user_data)
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"data": user})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.patch("/users/<int:user_id>/status")
def update_user_status(user_id: int):
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")

    if status is None:
        return (
            jsonify(
                {
                    "error": "Status field is required",
                }
            ),
            400,
        )

    if not isinstance(status, bool):
        return (
            jsonify(
                {
                    "error": "Status must be a boolean value",
                }
            ),
            400,
        )

    user = users_service.update_status(user_id, status)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"data": user})

@bp.get("/users/<int:session_id>/students-by-session")
def get_students_by_session(session_id: int):
    search = request.args.get("search")
    status = request.args.get("status")
    
    if status and status not in VALID_SESSION_STUDENT_STATUSES:
        return (
            jsonify(
                {
                    "error": "Invalid status value",
                    "allowed": list(VALID_SESSION_STUDENT_STATUSES),
                }
            ),
            400,
        )
    
    students = users_service.find_many_by_session_id(session_id, search=search, status=status)
    return jsonify({"data": students})

