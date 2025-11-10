from typing import Optional

from flask import Blueprint, jsonify, request

from services import courses as courses_service

bp = Blueprint("courses", __name__)


def _parse_status_param(raw_value: Optional[str]) -> Optional[bool]:
    if raw_value is None:
        return None

    lowered = raw_value.strip().lower()
    if lowered in {"true", "1", "yes"}:
        return True
    if lowered in {"false", "0", "no"}:
        return False
    return None


@bp.get("/courses")
def list_courses():
    status_filter = _parse_status_param(request.args.get("status"))
    courses = courses_service.find_many(status=status_filter)
    return jsonify({"data": courses})


@bp.get("/courses/<int:course_id>")
def get_course(course_id: int):
    course = courses_service.find_one(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    return jsonify({"data": course})


@bp.post("/courses")
def create_course():
    payload = request.get_json(silent=True) or {}

    name = payload.get("name")
    description = payload.get("description")
    semester = payload.get("semester")
    status = payload.get("status", True)

    if not name or not description or semester is None:
        return (
            jsonify(
                {
                    "error": "Missing required fields",
                    "required": ["name", "description", "semester"],
                }
            ),
            400,
        )

    try:
        course = courses_service.create(
            {
                "name": name,
                "description": description,
                "semester": semester,
                "status": bool(status),
            }
        )
        return jsonify({"data": course}), 201
    except Exception as exc:  # pragma: no cover - log friendly error
        return jsonify({"error": str(exc)}), 500


@bp.put("/courses/<int:course_id>")
def update_course(course_id: int):
    payload = request.get_json(silent=True) or {}
    allowed_fields = {"name", "description", "semester", "status"}
    update_data = {key: value for key, value in payload.items() if key in allowed_fields}

    if not update_data:
        return jsonify({"error": "No valid fields provided for update"}), 400

    course = courses_service.update(course_id, update_data)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    return jsonify({"data": course})


@bp.patch("/courses/<int:course_id>/status")
def update_course_status(course_id: int):
    payload = request.get_json(silent=True) or {}

    if "status" not in payload:
        return jsonify({"error": "Status field is required"}), 400

    course = courses_service.update_status(course_id, bool(payload["status"]))
    if not course:
        return jsonify({"error": "Course not found"}), 404

    return jsonify({"data": course})

