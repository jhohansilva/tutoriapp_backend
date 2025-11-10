from datetime import datetime
from flask import Blueprint, jsonify, request

from services import sessions as sessions_service

bp = Blueprint("sessions", __name__)

VALID_STATUSES = {"pending", "confirmed", "cancelled"}
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

    if level and level not in {"basic", "medium", "advanced"}:
        return (
            jsonify(
                {
                    "error": "Invalid level value",
                    "allowed": ["basic", "medium", "advanced"],
                }
            ),
            400,
        )

    for label, value in (("start_date", start_date), ("end_date", end_date)):
        if value and not _validate_date_param(value):
            return (
                jsonify(
                    {
                        "error": f"Invalid {label} format, expected YYYY-MM-DD",
                    }
                ),
                400,
            )

    sessions = sessions_service.find_many(
        search=search,
        level=level,
        start_date=start_date,
        end_date=end_date,
    )
    return jsonify({"data": sessions})


@bp.get("/sessions/<int:session_id>")
def get_session(session_id: int):
    session = sessions_service.find_one(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"data": session})


@bp.get("/sessions/tutor/<int:tutor_id>")
def get_sessions_by_tutor(tutor_id: int):
    sessions = sessions_service.find_many_by_tutor_id(tutor_id)
    return jsonify({"data": sessions})


@bp.get("/sessions/student/<int:student_id>")
def get_sessions_by_student(student_id: int):
    search = request.args.get("search")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    for label, value in (("start_date", start_date), ("end_date", end_date)):
        if value and not _validate_date_param(value):
            return (
                jsonify(
                    {
                        "error": f"Invalid {label} format, expected YYYY-MM-DD",
                    }
                ),
                400,
            )

    sessions = sessions_service.find_many_by_student_id(
        student_id,
        search=search,
        start_date=start_date,
        end_date=end_date,
    )
    return jsonify({"data": sessions})


@bp.post("/sessions")
def create_session():
    payload = request.get_json(silent=True) or {}

    required_fields = {"duration", "seats", "type", "tutor_id", "course_id"}
    missing = [field for field in required_fields if field not in payload]
    if missing:
        return (
            jsonify({"error": "Missing required fields", "required": missing}),
            400,
        )

    session_data = {
        "duration": payload["duration"],
        "seats": payload["seats"],
        "type": payload["type"],
        "tutor_id": payload["tutor_id"],
        "course_id": payload["course_id"],
    }

    if session_data["type"] not in {"online", "in_person"}:
        return (
            jsonify({"error": "Invalid type value", "allowed": ["online", "in_person"]}),
            400,
        )

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
        return (
            jsonify(
                {"error": "Invalid level value", "allowed": ["basic", "medium", "advanced"]}
            ),
            400,
        )

    status = session_data.get("status")
    if status and status not in VALID_STATUSES:
        return (
            jsonify({"error": "Invalid status value", "allowed": list(VALID_STATUSES)}),
            400,
        )

    session_data = {
        **session_data,
    }

    try:
        session = sessions_service.create_session(session_data)
        return jsonify({"data": session}), 201
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify({"error": str(exc)}), 500


@bp.patch("/sessions/<int:session_id>/status")
def update_session_status(session_id: int):
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")

    if status not in VALID_STATUSES:
        return (
            jsonify(
                {
                    "error": "Invalid status value",
                    "allowed": list(VALID_STATUSES),
                }
            ),
            400,
        )

    session = sessions_service.update_status(session_id, status)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    return jsonify({"data": session})

