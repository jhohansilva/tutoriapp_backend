from typing import Any, Dict, List, Optional

from prisma.errors import RecordNotFoundError
from services.db import get_db, run_in_persistent_loop


def _serialize_course(course: Any) -> Dict[str, Any]:
    return {
        "id": course.id,
        "code": course.code,
        "name": course.name,
        "description": course.description,
        "semester": course.semester,
        "status": course.status,
        "created_at": course.created_at.isoformat() if course.created_at else None,
        "updated_at": course.updated_at.isoformat() if course.updated_at else None,
    }


async def _find_many(
    search: Optional[str] = None,
    semester: Optional[int] = None,
    status: Optional[bool] = None,
) -> Dict[str, Any]:
    async with get_db() as db:
        try:
            where: Dict[str, Any] = {}
            
            if status is not None:
                where["status"] = status

            if semester is not None:
                where["semester"] = semester

            if search:
                where["OR"] = [
                    {"name": {"contains": search, "mode": "insensitive"}},
                    {"description": {"contains": search, "mode": "insensitive"}},
                    {"code": {"contains": search, "mode": "insensitive"}},
                ]

            courses = await db.courses.find_many(where=where or None)
            data = [_serialize_course(course) for course in courses]

            return {
                "totalRecords": len(data),
                "courses": data,
            }
        except Exception as e:
            print("[ERROR_COURSES] find_many: ", e)
            return {
                "totalRecords": 0,
                "courses": [],
            }


async def _find_one(course_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        course = await db.courses.find_unique(where={"id": course_id})
        return _serialize_course(course) if course else None


async def _create(data: Dict[str, Any]) -> Dict[str, Any]:
    async with get_db() as db:
        course = await db.courses.create(data=data)
        return _serialize_course(course)


async def _update(course_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        try:
            course = await db.courses.update(where={"id": course_id}, data=data)
            return _serialize_course(course)
        except RecordNotFoundError:
            return None


async def _update_status(course_id: int, status: bool) -> Optional[Dict[str, Any]]:
    return await _update(course_id, {"status": status})


def find_many(
    search: Optional[str] = None,
    semester: Optional[int] = None,
    status: Optional[bool] = None,
) -> Dict[str, Any]:
    return run_in_persistent_loop(_find_many(search, semester, status))


def find_one(course_id: int) -> Optional[Dict[str, Any]]:
    return run_in_persistent_loop(_find_one(course_id))


def create(data: Dict[str, Any]) -> Dict[str, Any]:
    return run_in_persistent_loop(_create(data))


def update(course_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return run_in_persistent_loop(_update(course_id, data))


def update_status(course_id: int, status: bool) -> Optional[Dict[str, Any]]:
    return run_in_persistent_loop(_update_status(course_id, status))

