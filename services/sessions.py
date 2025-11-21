from datetime import datetime, time, timedelta
from calendar import monthrange
from typing import Any, Dict, List, Optional

from prisma.errors import RecordNotFoundError
from services.db import get_db, run_in_persistent_loop


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

            # Filtrar por intervalo de fechas usando start_date de la sesión
            start_dt = _parse_date_param(start_date)
            end_dt = _parse_date_param(end_date, end_of_day=True)
            
            if start_dt and end_dt:
                # Si hay ambas fechas, crear un rango
                where["start_date"] = {
                    "gte": start_dt,
                    "lte": end_dt
                }
            elif start_dt:
                # Solo fecha inicio: sesiones desde start_date en adelante
                where["start_date"] = {
                    "gte": start_dt
                }
            elif end_dt:
                # Solo fecha fin: sesiones hasta end_date
                where["start_date"] = {
                    "lte": end_dt
                }

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
    return run_in_persistent_loop(_find_one(session_id))


def find_many_by_tutor_id(
    tutor_id: int,
    search: Optional[str] = None,
    level: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    return run_in_persistent_loop(_find_many_by_tutor_id(tutor_id, search, level, start_date, end_date, status))


def find_many(
    search: Optional[str] = None,
    level: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    exclude_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    return run_in_persistent_loop(_find_many(search, level, start_date, end_date, status, limit, exclude_user_id))


def find_many_by_student_id(
    student_id: int,
    search: Optional[str] = None,
    level: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    return run_in_persistent_loop(
        _find_many_by_student_id(student_id, search, level, start_date, end_date, status)
    )


def create_session(data: Dict[str, Any]) -> Dict[str, Any]:
    return run_in_persistent_loop(_create_session(data))


def update_status(session_id: int, status: str) -> Optional[Dict[str, Any]]:
    return run_in_persistent_loop(_update_status(session_id, status))

def update_session_student_status(
    session_id: int,
    student_id: int,
    status: str,
    attended: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    return run_in_persistent_loop(
        _update_session_student_status(session_id, student_id, status, attended)
    )


def create_session_student(
    session_id: int,
    student_id: int,
    status: Optional[str] = None,
    attended: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    return run_in_persistent_loop(
        _create_session_student(session_id, student_id, status, attended)
    )


async def _get_student_stats(student_id: int) -> Dict[str, Any]:
    """Get comprehensive statistics for a student dashboard."""
    async with get_db() as db:
        try:
            now = datetime.now()
            
            # Calcular inicio y fin del mes actual para month_sessions
            start_of_month = datetime(now.year, now.month, 1)
            end_of_month = datetime(
                now.year, 
                now.month, 
                monthrange(now.year, now.month)[1],
                time.max.hour, 
                time.max.minute, 
                time.max.second
            )
            
            # confirmed_sessions: sesiones confirmadas a partir de la fecha actual
            confirmed_sessions = await db.sessionstudents.count(
                where={
                    "student_id": student_id,
                    "status": "registered",
                    "session": {
                        "start_date": {
                            "gte": now
                        },
                        "status": "confirmed"
                    }
                }
            )
            
            # pending_sessions: sesiones pendientes a partir de la fecha actual
            pending_sessions = await db.sessionstudents.count(
                where={
                    "student_id": student_id,
                    "status": "registered",
                    "session": {
                        "start_date": {
                            "gte": now
                        },
                        "status": "pending"
                    }
                }
            )
            
            # month_sessions: sesiones inscritas en el mes actual
            month_sessions = await db.sessionstudents.count(
                where={
                    "student_id": student_id,
                    "created_at": {
                        "gte": start_of_month,
                        "lte": end_of_month
                    }
                }
            )
            
            # next_tutoring: mantener como está
            next_tutoring_enrollment = await db.sessionstudents.find_first(
                where={
                    "student_id": student_id,
                    "session": {
                        "start_date": {
                            "gt": now
                        }
                    }
                },
                include={
                    "session": {
                        "include": {
                            "course": True,
                            "tutor": True,
                            "students": True
                        }
                    }
                },
                order={
                    "session": {
                        "start_date": "asc"
                    }
                }
            )
            
            next_tutoring = None
            if next_tutoring_enrollment and next_tutoring_enrollment.session:
                session = next_tutoring_enrollment.session
                next_tutoring = {
                    "course_name": session.course.name if session.course else None,
                    "start_date": session.start_date.isoformat() if session.start_date else None
                }
            
            # Suma de horas de sesiones asistidas/atendidas
            attended_sessions = await db.sessionstudents.find_many(
                where={
                    "student_id": student_id,
                    "attended": True
                },
                include={
                    "session": True
                }
            )
            
            total_hours = 0
            for enrollment in attended_sessions:
                if enrollment.session and enrollment.session.duration:
                    # Duración está en minutos, convertir a horas
                    total_hours += enrollment.session.duration / 60.0
            
            # Promedio de horas de sesiones inscritas
            registered_sessions = await db.sessionstudents.find_many(
                where={
                    "student_id": student_id,
                    "status": "registered"
                },
                include={
                    "session": True
                }
            )
            
            total_hours_registered = 0
            sessions_count = 0
            for enrollment in registered_sessions:
                if enrollment.session and enrollment.session.duration:
                    # Duración está en minutos, convertir a horas
                    total_hours_registered += enrollment.session.duration / 60.0
                    sessions_count += 1
            
            average_hours = round(total_hours_registered / sessions_count, 2) if sessions_count > 0 else 0.0
            
            return {
                "confirmed_sessions": confirmed_sessions,
                "pending_sessions": pending_sessions,
                "month_sessions": month_sessions,
                "next_session": next_tutoring,
                "total_hours_attended": round(total_hours, 2),
                "average_hours_registered": average_hours
            }
            
        except Exception as e:
            print(f"[ERROR_STUDENT_STATS] Error getting student stats: {e}")
            return {
                "confirmed_sessions": 0,
                "pending_sessions": 0,
                "month_sessions": 0,
                "next_session": None,
                "total_hours_attended": 0.0,
                "average_hours_registered": 0.0
            }


async def _get_student_stats_history(student_id: int) -> Dict[str, Any]:
    """Get statistics history for past sessions of a student."""
    async with get_db() as db:
        try:
            now = datetime.now()
            
            # Obtener todas las sesiones pasadas del estudiante (donde start_date < now)
            past_sessions = await db.sessionstudents.find_many(
                where={
                    "student_id": student_id,
                    "session": {
                        "start_date": {
                            "lt": now
                        }
                    }
                },
                include={
                    "session": True
                }
            )
            
            # Sesiones atendidas (attended = True)
            attended_sessions = [enrollment for enrollment in past_sessions if enrollment.attended is True]
            attended_count = len(attended_sessions)
            
            # Horas totales de las sesiones atendidas
            total_hours_attended = 0
            for enrollment in attended_sessions:
                if enrollment.session and enrollment.session.duration:
                    # Duración está en minutos, convertir a horas
                    total_hours_attended += enrollment.session.duration / 60.0
            
            # Total de sesiones pasadas
            total_past_sessions = len(past_sessions)
            
            # Promedio de asistencia (porcentaje)
            attendance_rate = round((attended_count / total_past_sessions * 100), 2) if total_past_sessions > 0 else 0.0
            
            # Sesiones inasistidas (status = "absent" y sesión pasada)
            unattended_sessions = [enrollment for enrollment in past_sessions if enrollment.status == "absent"]
            unattended_count = len(unattended_sessions)
            
            return {
                "attended_sessions": attended_count,
                "total_hours_attended": round(total_hours_attended, 2),
                "attendance_rate": attendance_rate,
                "unattended_sessions": unattended_count
            }
            
        except Exception as e:
            print(f"[ERROR_STUDENT_STATS_HISTORY] Error getting student stats history: {e}")
            return {
                "attended_sessions": 0,
                "total_hours_attended": 0.0,
                "attendance_rate": 0.0,
                "unattended_sessions": 0
            }


def get_student_stats(student_id: int) -> Dict[str, Any]:
    """Synchronously get student statistics."""
    return run_in_persistent_loop(_get_student_stats(student_id))


async def _get_tutor_stats(tutor_id: int) -> Dict[str, Any]:
    """Get comprehensive statistics for a tutor dashboard."""
    async with get_db() as db:
        try:
            now = datetime.now()
            
            # Calcular inicio y fin del día actual
            start_of_day = datetime.combine(now.date(), time.min)
            end_of_day = datetime.combine(now.date(), time.max)
            
            # Total de estudiantes únicos que han estado en sesiones del tutor
            all_sessions = await db.sessions.find_many(
                where={"tutor_id": tutor_id},
                include={"students": True}
            )
            
            unique_students = set()
            for session in all_sessions:
                for student_enrollment in session.students:
                    unique_students.add(student_enrollment.student_id)
            total_estudiantes = len(unique_students)
            
            # Sesiones del día actual
            sessions_today = await db.sessions.count(
                where={
                    "tutor_id": tutor_id,
                    "start_date": {
                        "gte": start_of_day,
                        "lte": end_of_day
                    }
                }
            )
            
            # Total de tutorías
            total_tutorias = len(all_sessions)
            
            # Porcentaje de sesiones completadas (status "confirmed" o que ya pasaron)
            completed_sessions = await db.sessions.count(
                where={
                    "tutor_id": tutor_id,
                    "OR": [
                        {"status": "confirmed"},
                        {"start_date": {"lt": now}}
                    ]
                }
            )
            porcentaje_completadas = round((completed_sessions / total_tutorias * 100), 2) if total_tutorias > 0 else 0.0
            
            # Duración promedio por sesión
            total_duration = sum(session.duration for session in all_sessions if session.duration)
            duracion_promedio = round(total_duration / total_tutorias, 2) if total_tutorias > 0 else 0.0
            
            # Ocupación promedio total (estudiantes inscritos / cupos) de todas las sesiones
            total_occupancies = []
            for session in all_sessions:
                enrolled_count = len(session.students) if session.students else 0
                seats = session.seats if session.seats else 1
                occupancy = (enrolled_count / seats * 100) if seats > 0 else 0.0
                total_occupancies.append(occupancy)
            
            # Calcular promedio total de ocupación
            ocupacion_promedio_total = round(sum(total_occupancies) / len(total_occupancies), 2) if total_occupancies else 0.0
            
            # Próxima sesión
            next_session = await db.sessions.find_first(
                where={
                    "tutor_id": tutor_id,
                    "start_date": {
                        "gt": now
                    }
                },
                include={
                    "course": True,
                    "tutor": True,
                    "students": True
                },
                order={
                    "start_date": "asc"
                }
            )
            
            proxima_sesion = None
            if next_session:
                proxima_sesion = {
                    "title": next_session.title,
                    "start_date": next_session.start_date.isoformat() if next_session.start_date else None,
                }
            
            return {
                "total_students": total_estudiantes,
                "today_sessions": sessions_today,
                "completed_sessions_percentage": porcentaje_completadas,
                "average_duration_per_session": duracion_promedio,
                "total_tutoring_sessions": total_tutorias,
                "average_occupancy_by_course": ocupacion_promedio_total,
                "next_session": proxima_sesion
            }
            
        except Exception as e:
            print(f"[ERROR_TUTOR_STATS] Error getting tutor stats: {e}")
            return {
                "total_students": 0,
                "today_sessions": 0,
                "completed_sessions_percentage": 0.0,
                "average_duration_per_session": 0.0,
                "total_tutoring_sessions": 0,
                "average_occupancy_by_course": 0.0,
                "next_session": None
            }


def get_student_stats_history(student_id: int) -> Dict[str, Any]:
    """Synchronously get student statistics history."""
    return run_in_persistent_loop(_get_student_stats_history(student_id))


def get_tutor_stats(tutor_id: int) -> Dict[str, Any]:
    """Synchronously get tutor statistics."""
    return run_in_persistent_loop(_get_tutor_stats(tutor_id))