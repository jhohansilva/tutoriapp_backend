from typing import Optional

from flask import Blueprint, request, g

from services import courses as courses_service
from app.routes.response_utils import success_response, error_response
from app.middleware import require_auth

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
    search = request.args.get("search")
    semester_param = request.args.get("semester")
    status_filter = _parse_status_param(request.args.get("status"))

    if semester_param:
        try:
            semester = int(semester_param)
        except ValueError:
            return error_response("Invalid semester value, expected an integer", 400)
    else:
        semester = None

    courses = courses_service.find_many(
        search=search,
        semester=semester,
        status=status_filter,
    )
    return success_response(courses)


@bp.get("/courses/<int:course_id>")
def get_course(course_id: int):
    course = courses_service.find_one(course_id)
    if not course:
        return error_response("Course not found", 404)
    return success_response(course)


@bp.post("/courses")
@require_auth
def create_course():
    payload = request.get_json(silent=True) or {}
    
    code = payload.get("code")
    name = payload.get("name")
    description = payload.get("description")
    semester = payload.get("semester")
    status = payload.get("status", True)

    if not code or not name or not description or semester is None:
        return error_response("Missing required fields: code, name, description, semester", 400)

    try:
        course = courses_service.create(
            {
                "code": code,
                "name": name,
                "description": description,
                "semester": semester,
                "status": bool(status),
            }
        )
        return success_response(course, "Curso creado exitosamente", 201)
    except Exception as exc:  # pragma: no cover - log friendly error
        return error_response(str(exc), 500)


@bp.put("/courses/<int:course_id>")
@require_auth
def update_course(course_id: int):
    payload = request.get_json(silent=True) or {}
    allowed_fields = {"code", "name", "description", "semester", "status"}
    update_data = {key: value for key, value in payload.items() if key in allowed_fields}

    if not update_data:
        return error_response("No valid fields provided for update", 400)

    course = courses_service.update(course_id, update_data)
    if not course:
        return error_response("Course not found", 404)

    return success_response(course, "Curso actualizado exitosamente")


@bp.patch("/courses/<int:course_id>/status")
@require_auth
def update_course_status(course_id: int):
    payload = request.get_json(silent=True) or {}

    if "status" not in payload:
        return error_response("Status field is required", 400)

    course = courses_service.update_status(course_id, bool(payload["status"]))
    if not course:
        return error_response("Course not found", 404)

    return success_response(course, "Estado del curso actualizado exitosamente")

