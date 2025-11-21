import asyncio
from datetime import datetime, time
from typing import Any, Dict, List, Optional

from prisma.errors import RecordNotFoundError
from services.db import get_db


def _session_to_dict(session: Any, include_students: bool = True) -> Dict[str, Any]:
    """Serialize a session record (and included relations) to a JSON-ready dict."""
    data = session.model_dump(mode="json")
    if not include_students:
        data.pop("students", None)
    return data


def _enrollment_to_dict(enrollment: Any) -> Dict[str, Any]:
    """Serialize a SessionStudents enrollment record to a JSON-ready dict."""
    return enrollment.model_dump(mode="json")


def _parse_date_param(value: Optional[str], *, end_of_day: bool = False) -> Optional[datetime]:
    """Parse YYYY-MM-DD strings into aware datetimes suitable for Prisma filters."""
    if not value:
        return None

    dt = datetime.strptime(value, "%Y-%m-%d")
    return datetime.combine(dt.date(), time.max if end_of_day else time.min)


async def _find_one(session_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        session = await db.sessions.find_unique(
            where={"id": session_id},
            include={"course": True, "tutor": True, "students": True},
        )
        return _session_to_dict(session) if session else None


async def _find_many_by_tutor_id(
    tutor_id: int,
    search: Optional[str] = None,
    level: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    async with get_db() as db:
        try:
            where: Dict[str, Any] = {"tutor_id": tutor_id}
            
            if level:
                where["level"] = level

            if status:
                where["status"] = status

            if search:
                where["OR"] = [
                    {"title": {"contains": search, "mode": "insensitive"}},
                    {"course": {"name": {"contains": search, "mode": "insensitive"}}},
                ]

            start_dt = _parse_date_param(start_date)
            if start_dt:
                where.setdefault("start_date", {})["gte"] = start_dt

            end_dt = _parse_date_param(end_date, end_of_day=True)
            if end_dt:
                where.setdefault("end_date", {})["lte"] = end_dt

            sessions = await db.sessions.find_many(
                where=where,
                order={
                    "start_date": "asc",
                },
                include={"course": True, "tutor": True, "students": True},
            )

            data = [_session_to_dict(session) for session in sessions]

            return {
                "totalRecords": len(data),
                "sessions": data,
            }
        except Exception as e:
            print("[ERROR_SESSIONS] find_many_by_tutor_id: ", e)
            return {
                "totalRecords": 0,
                "sessions": [],
            }


async def _find_many(
    search: Optional[str] = None,
    level: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    exclude_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    async with get_db() as db:
        try:
            where: Dict[str, Any] = {}
            if level:
                where["level"] = level

            if status:
                where["status"] = status

            if search:
                where["OR"] = [
                    {"title": {"contains": search, "mode": "insensitive"}},
                    {"course": {"name": {"contains": search, "mode": "insensitive"}}},
                ]

            start_dt = _parse_date_param(start_date)
            if start_dt:
                where.setdefault("start_date", {})["gte"] = start_dt

            end_dt = _parse_date_param(end_date, end_of_day=True)
            if end_dt:
                where.setdefault("end_date", {})["lte"] = end_dt

            # Excluir sesiones donde el usuario ya está inscrito como estudiante
            if exclude_user_id:
                where["NOT"] = {
                    "students": {
                        "some": {
                            "student_id": exclude_user_id
                        }
                    }
                }

            # Construir los argumentos de find_many
            find_args: Dict[str, Any] = {
                "where": where or None,
                "order": {
                    "start_date": "asc",
                },
                "include": {
                    "course": True,
                    "tutor": True,
                    "students": True,
                },
            }
            
            # Solo agregar take si limit tiene un valor
            if limit:
                find_args["take"] = limit

            sessions = await db.sessions.find_many(**find_args)

            data = []
            for session in sessions:
                session_dict = _session_to_dict(session)
                # Agregar el campo enrolled con la cantidad de estudiantes
                students = session_dict.get("students", [])
                session_dict["enrolled"] = len(students) if students else 0
                data.append(session_dict)

            return {
                "totalRecords": len(data),
                "sessions": data,
            }

        except Exception as e:
            print("[ERROR_SESSIONS] find_many: ", e)
            return {
                "totalRecords": 0,
                "sessions": [],
            }


async def _find_many_by_student_id(
    student_id: int,
    search: Optional[str] = None,
    level: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    async with get_db() as db:
        try:
            where: Dict[str, Any] = {
                "students": {
                    "some": {
                        "student_id": student_id,
                    }
                }
            }

            if level:
                where["level"] = level

            if status:
                where["status"] = status

            if search:
                where["OR"] = [
                    {"title": {"contains": search, "mode": "insensitive"}},
                    {"course": {"name": {"contains": search, "mode": "insensitive"}}},
                ]

            start_dt = _parse_date_param(start_date)
            if start_dt:
                where.setdefault("start_date", {})["gte"] = start_dt

            end_dt = _parse_date_param(end_date, end_of_day=True)
            if end_dt:
                where.setdefault("end_date", {})["lte"] = end_dt

            sessions = await db.sessions.find_many(
                where=where,
                order={
                    "start_date": "asc",
                },
                include={"course": True, "tutor": True, "students": True},
            )

            sessions_payload: List[Dict[str, Any]] = []
            for session in sessions:
                session_dict = _session_to_dict(session)
                students = session_dict.get("students", [])
                attendance = next(
                    (item for item in students if item.get("student_id") == student_id),
                    None,
                )
                session_dict["attendance"] = attendance
                session_dict["students"] = [attendance] if attendance else []
                sessions_payload.append(session_dict)

            return {
                "totalRecords": len(sessions_payload),
                "sessions": sessions_payload,
            }
        except Exception as e:
            print("[ERROR_SESSIONS] find_many_by_student_id: ", e)
            return {
                "totalRecords": 0,
                "sessions": [],
            }


async def _create_session(data: Dict[str, Any]) -> Dict[str, Any]:
    async with get_db() as db:
        session = await db.sessions.create(
            data=data,
            include={"course": True, "tutor": True, "students": True},
        )
        return _session_to_dict(session)


async def _update_status(session_id: int, status: str) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        try:
            session = await db.sessions.update(
                where={"id": session_id},
                data={"status": status},
                include={"course": True, "tutor": True, "students": True},
            )
            return _session_to_dict(session)
        except RecordNotFoundError:
            return None

async def _update_session_student_status(
    session_id: int,
    student_id: int,
    status: str,
    attended: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        try:
            data = {"status": status}

            # El campo attended es opcional
            if attended is not None:
                data["attended"] = attended

            # Find the enrollment first using the composite unique constraint
            enrollment = await db.sessionstudents.find_first(
                where={
                    "session_id": session_id,
                    "student_id": student_id,
                }
            )
            
            if not enrollment:
                raise RecordNotFoundError("Enrollment not found")
            
            # Update using the id
            enrollment = await db.sessionstudents.update(
                where={"id": enrollment.id},
                data=data,
                include={
                    "session": True,
                    "student": True,
                },
            )

            return _enrollment_to_dict(enrollment)

        except RecordNotFoundError:
            return None


async def _create_session_student(
    session_id: int,
    student_id: int,
    status: Optional[str] = None,
    attended: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        try:
            # Verificar que la sesión existe
            session = await db.sessions.find_unique(where={"id": session_id})
            if not session:
                return None

            # Verificar que el estudiante existe
            student = await db.user.find_unique(where={"id": student_id})
            if not student:
                return None

            # Verificar si ya existe un registro para esta combinación session_id + student_id
            existing = await db.sessionstudents.find_first(
                where={
                    "session_id": session_id,
                    "student_id": student_id,
                }
            )
            if existing:
                return None  # Ya existe, se debe usar el endpoint de actualización

            # Preparar los datos
            data: Dict[str, Any] = {
                "session_id": session_id,
                "student_id": student_id,
            }

            if status:
                data["status"] = status

            if attended is not None:
                data["attended"] = attended

            # Crear el registro
            enrollment = await db.sessionstudents.create(
                data=data,
                include={
                    "session": True,
                    "student": True,
                },
            )

            return _enrollment_to_dict(enrollment)

        except Exception as e:
            print(f"[ERROR_SESSIONS] create_session_student: {e}")
            return None


def find_one(session_id: int) -> Optional[Dict[str, Any]]:
    return asyncio.run(_find_one(session_id))


def find_many_by_tutor_id(
    tutor_id: int,
    search: Optional[str] = None,
    level: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    return asyncio.run(_find_many_by_tutor_id(tutor_id, search, level, start_date, end_date, status))


def find_many(
    search: Optional[str] = None,
    level: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    exclude_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    return asyncio.run(_find_many(search, level, start_date, end_date, status, limit, exclude_user_id))


def find_many_by_student_id(
    student_id: int,
    search: Optional[str] = None,
    level: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    return asyncio.run(
        _find_many_by_student_id(student_id, search, level, start_date, end_date, status)
    )


def create_session(data: Dict[str, Any]) -> Dict[str, Any]:
    return asyncio.run(_create_session(data))


def update_status(session_id: int, status: str) -> Optional[Dict[str, Any]]:
    return asyncio.run(_update_status(session_id, status))

def update_session_student_status(
    session_id: int,
    student_id: int,
    status: str,
    attended: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    return asyncio.run(
        _update_session_student_status(session_id, student_id, status, attended)
    )


def create_session_student(
    session_id: int,
    student_id: int,
    status: Optional[str] = None,
    attended: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    return asyncio.run(
        _create_session_student(session_id, student_id, status, attended)
    )