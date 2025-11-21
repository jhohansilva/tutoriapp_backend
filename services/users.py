import asyncio
import bcrypt
from typing import Any, Dict, List, Optional

from prisma.errors import RecordNotFoundError
from services.db import get_db


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _user_to_dict(user: Any) -> Dict[str, Any]:
    """Convert Prisma user model to dict."""
    data = user.model_dump(mode="json")
    # Remove password from response for security
    data.pop("password", None)
    return data


async def _find_one(user_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        try:
            user = await db.user.find_unique(where={"id": user_id})
            return _user_to_dict(user) if user else None
        except Exception as e:
            print("[ERROR_USERS] find_one: ", e)
            return None


async def _find_many(
    role: Optional[str] = None,
    status: Optional[bool] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    async with get_db() as db:
        try:
            where: Dict[str, Any] = {}

            if role:
                where["role"] = role

            if status is not None:
                where["status"] = status

            if search:
                where["OR"] = [
                    {"email": {"contains": search, "mode": "insensitive"}},
                    {"name": {"contains": search, "mode": "insensitive"}},
                ]

            users = await db.user.find_many(
                where=where or None,
                order={"name": "asc"},
            )

            data = [_user_to_dict(user) for user in users]

            return {
                "totalRecords": len(data),
                "users": data,
            }
        except Exception as e:
            print("[ERROR_USERS] find_many: ", e)
            return {
                "totalRecords": 0,
                "users": [],
            }


async def _create_user(data: Dict[str, Any]) -> Dict[str, Any]:
    async with get_db() as db:
        # Hash password before storing
        if "password" in data:
            data["password"] = _hash_password(data["password"])
        try:
            user = await db.user.create(data=data)
            return _user_to_dict(user)
        except Exception as e:
            print("[ERROR_USERS] create: ", e)
            raise


async def _update_user(user_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        # Hash password if it's being updated
        if "password" in data:
            data["password"] = _hash_password(data["password"])
        try:
            user = await db.user.update(
                where={"id": user_id},
                data=data,
            )
            return _user_to_dict(user)
        except RecordNotFoundError:
            return None
        except Exception as e:
            print("[ERROR_USERS] update: ", e)
            raise


async def _update_status(user_id: int, status: bool) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        try:
            user = await db.user.update(
                where={"id": user_id},
                data={"status": status},
            )
            return _user_to_dict(user)
        except RecordNotFoundError:
            return None
        except Exception as e:
            print("[ERROR_USERS] update_status: ", e)
            return None


async def _find_many_by_session_id(
    session_id: int, 
    search: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    async with get_db() as db:
        try:
            session_attendance_filter: Dict[str, Any] = {"session_id": session_id}
            if status:
                session_attendance_filter["status"] = status

            where: Dict[str, Any] = {
                "session_attendances": {"some": session_attendance_filter}
            }

            if search:
                where = {
                    "AND": [
                        {"session_attendances": {"some": session_attendance_filter}},
                        {
                            "OR": [
                                {"email": {"contains": search, "mode": "insensitive"}},
                                {"name": {"contains": search, "mode": "insensitive"}},
                            ]
                        }
                    ]
                }

            students = await db.user.find_many(where=where)
            data = [_user_to_dict(student) for student in students]

            return {
                "totalRecords": len(data),
                "students": data,
            }
        except Exception as e:
            print("[ERROR_USERS] find_many_by_session_id: ", e)
            return {
                "totalRecords": 0,
                "students": [],
            }


def find_one(user_id: int) -> Optional[Dict[str, Any]]:
    return asyncio.run(_find_one(user_id))


def find_many(
    role: Optional[str] = None,
    status: Optional[bool] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    return asyncio.run(_find_many(role, status, search))


def create_user(data: Dict[str, Any]) -> Dict[str, Any]:
    return asyncio.run(_create_user(data))


def update_user(user_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return asyncio.run(_update_user(user_id, data))


def update_status(user_id: int, status: bool) -> Optional[Dict[str, Any]]:
    return asyncio.run(_update_status(user_id, status))


def find_many_by_session_id(
    session_id: int, 
    search: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    return asyncio.run(_find_many_by_session_id(session_id, search, status))
