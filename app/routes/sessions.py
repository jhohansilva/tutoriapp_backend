from datetime import datetime
from flask import Blueprint, request

from services import sessions as sessions_service
from app.routes.response_utils import success_response, error_response

bp = Blueprint("sessions", __name__)

VALID_STATUSES = {"pending", "confirmed", "cancelled"}
VALID_ENROLLMENT_STATUSES = {"requested", "registered", "absent", "attended", "rejected"}
DATE_FORMAT = "%Y-%m-%d"


def _validate_date_param(value: str) -> bool:
    try:
        datetime.strptime(value, DATE_FORMAT)
        return True
    except (TypeError, ValueError):
        return False


@bp.get("/sessions")
def list_sessions():
    search = request.args.get("search")
    level = request.args.get("level")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    status = request.args.get("status")
    limit_str = request.args.get("limit")
    
    # Convertir limit a int si está presente
    limit = None
    if limit_str:
        try:
            limit = int(limit_str)
            if limit <= 0:
                return jsonify({"error": "limit must be a positive integer"}), 400
        except ValueError:
            return jsonify({"error": "limit must be a valid integer"}), 400

    if level and level not in {"basic", "medium", "advanced"}:
        return error_response("Invalid level value. Allowed values: basic, medium, advanced", 400)

    if status and status not in VALID_STATUSES:
        return error_response(f"Invalid status value. Allowed values: {', '.join(VALID_STATUSES)}", 400)

    for label, value in (("start_date", start_date), ("end_date", end_date)):
        if value and not _validate_date_param(value):
            return error_response(f"Invalid {label} format, expected YYYY-MM-DD", 400)

    sessions = sessions_service.find_many(
        search=search,
        level=level,
        start_date=start_date,
        end_date=end_date,
        status=status,
        limit=limit,
    )
    return success_response(sessions)


@bp.get("/sessions/<int:session_id>")
def get_session(session_id: int):
    session = sessions_service.find_one(session_id)
    if not session:
        return error_response("Session not found", 404)
    return success_response(session)


@bp.get("/sessions/tutor/<int:tutor_id>")
def get_sessions_by_tutor(tutor_id: int):
    search = request.args.get("search")
    level = request.args.get("level")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    status = request.args.get("status")

    if level and level not in {"basic", "medium", "advanced"}:
        return error_response("Invalid level value. Allowed values: basic, medium, advanced", 400)

    if status and status not in VALID_STATUSES:
        return error_response(f"Invalid status value. Allowed values: {', '.join(VALID_STATUSES)}", 400)

    for label, value in (("start_date", start_date), ("end_date", end_date)):
        if value and not _validate_date_param(value):
            return error_response(f"Invalid {label} format, expected YYYY-MM-DD", 400)

    sessions = sessions_service.find_many_by_tutor_id(
        tutor_id,
        search=search,
        level=level,
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    return success_response(sessions)


@bp.get("/sessions/student/<int:student_id>")
def get_sessions_by_student(student_id: int):
    search = request.args.get("search")
    level = request.args.get("level")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    status = request.args.get("status")

    if level and level not in {"basic", "medium", "advanced"}:
        return error_response("Invalid level value. Allowed values: basic, medium, advanced", 400)

    if status and status not in VALID_STATUSES:
        return error_response(f"Invalid status value. Allowed values: {', '.join(VALID_STATUSES)}", 400)

    for label, value in (("start_date", start_date), ("end_date", end_date)):
        if value and not _validate_date_param(value):
            return error_response(f"Invalid {label} format, expected YYYY-MM-DD", 400)

    sessions = sessions_service.find_many_by_student_id(
        student_id,
        search=search,
        level=level,
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    return success_response(sessions)


@bp.post("/sessions")
def create_session():
    payload = request.get_json(silent=True) or {}

    required_fields = {"duration", "seats", "type", "tutor_id", "course_id"}
    missing = [field for field in required_fields if field not in payload]
    if missing:
        return error_response(f"Missing required fields: {', '.join(missing)}", 400)

    session_data = {
        "duration": payload["duration"],
        "seats": payload["seats"],
        "type": payload["type"],
        "tutor_id": payload["tutor_id"],
        "course_id": payload["course_id"],
    }

    if session_data["type"] not in {"online", "in_person"}:
        return error_response("Invalid type value. Allowed values: online, in_person", 400)

    optional_fields = {
        "title",
        "description",
        "start_date",
        "end_date",
        "level",
        "status",
        "class_room",
    }
    for field in optional_fields:
        if field in payload and payload[field] is not None:
            session_data[field] = payload[field]

    level = session_data.get("level")
    if level and level not in {"basic", "medium", "advanced"}:
        return error_response("Invalid level value. Allowed values: basic, medium, advanced", 400)

    status = session_data.get("status")
    if status and status not in VALID_STATUSES:
        return error_response(f"Invalid status value. Allowed values: {', '.join(VALID_STATUSES)}", 400)

    session_data = {
        **session_data,
    }

    try:
        session = sessions_service.create_session(session_data)
        return success_response(session, "Sesión creada exitosamente", 201)
    except Exception as exc:  # pragma: no cover - defensive
        return error_response(str(exc), 500)


@bp.patch("/sessions/<int:session_id>/status")
def update_session_status(session_id: int):
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")


    if status not in VALID_STATUSES:
        return error_response(f"Invalid status value. Allowed values: {', '.join(VALID_STATUSES)}", 400)

    session = sessions_service.update_status(session_id, status)
    if not session:
        return error_response("Session not found", 404)

    return success_response(session, "Estado de la sesión actualizado exitosamente")

@bp.post("/sessions/<int:session_id>/students")
def create_session_student(session_id: int):
    """Create a new enrollment (SessionStudents record) for a student in a session."""
    payload = request.get_json(silent=True) or {}

    student_id = payload.get("student_id")
    status = payload.get("status", "registered")
    attended = payload.get("attended", False)

    if not student_id:
        return error_response("Missing required field: student_id", 400)

    if not isinstance(student_id, int):
        return error_response("student_id must be an integer", 400)

    if status not in VALID_ENROLLMENT_STATUSES:
        return error_response(f"Invalid status value. Allowed values: {', '.join(VALID_ENROLLMENT_STATUSES)}", 400)

    if not isinstance(attended, bool):
        return error_response("attended must be a boolean value", 400)

    enrollment = sessions_service.create_session_student(
        session_id=session_id,
        student_id=student_id,
        status=status,
        attended=attended,
    )

    if not enrollment:
        return error_response("Session not found, student not found, or enrollment already exists", 404)

    return success_response(enrollment, "Estudiante inscrito en la sesión exitosamente", 201)


@bp.patch("/sessions/<int:session_id>/students/<int:student_id>/status")
def update_session_student_status(session_id: int, student_id: int):
    payload = request.get_json(silent=True) or {}

    status = payload.get("status")
    attended = payload.get("attended")

    if not status:
        return error_response("Missing required field: status", 400)

    if status not in VALID_ENROLLMENT_STATUSES:
        return error_response(f"Invalid status value. Allowed values: {', '.join(VALID_ENROLLMENT_STATUSES)}", 400)

    updated = sessions_service.update_session_student_status(
        session_id=session_id,
        student_id=student_id,
        status=status,
        attended=attended,
    )

    if not updated:
        return error_response("Enrollment not found", 404)

    return success_response(updated, "Estado del estudiante en la sesión actualizado exitosamente")

