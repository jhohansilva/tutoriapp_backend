import asyncio
import os
from typing import Any, Dict, Optional
from jwt import encode as jwt_encode

from prisma import Prisma

prisma = Prisma()

SECRET_KEY = os.getenv("JWT_SECRET", "secret-key")

async def _login(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Async helper to login a user using Prisma."""
    await prisma.connect()
    print('data', email, password)

    try:
        user = await prisma.user.find_first(where={"email": email})
        if not user or user.password != password:
            return None

        token = jwt_encode({"user_id": user.id}, SECRET_KEY, algorithm="HS256")
        return {
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            },
        }
    except Exception as e:
        print('[ERROR_LOGIN]', e)
        return None
    finally:
        await prisma.disconnect()


def login(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Synchronously login a user by invoking the async Prisma client."""
    return asyncio.run(_login(email, password))