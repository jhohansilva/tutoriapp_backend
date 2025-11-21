import asyncio
import os
from typing import Any, Dict, Optional
from jwt import encode as jwt_encode, decode as jwt_decode
from jwt.exceptions import InvalidTokenError, DecodeError, ExpiredSignatureError
import bcrypt

from services.db import get_db

SECRET_KEY = os.getenv("JWT_SECRET", "secret-key")

async def _login(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Async helper to login a user using Prisma."""
    async with get_db() as db:
        try:
            user = await db.user.find_first(where={"email": email})
            if not user:
                return None
            
            # Verify password with bcrypt
            if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
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


def login(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Synchronously login a user by invoking the async Prisma client."""
    return asyncio.run(_login(email, password))


async def _verify_token_and_get_user(token: str) -> Optional[Dict[str, Any]]:
    """Async helper to verify JWT token and get user information."""
    try:
        # Decode and verify the token
        payload = jwt_decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        
        if not user_id:
            return None
        
        # Get user from database
        async with get_db() as db:
            user = await db.user.find_unique(where={"id": user_id})
            if not user or not user.status:
                return None
            
            return {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "name": user.name,
                "status": user.status,
            }
    except (InvalidTokenError, DecodeError, ExpiredSignatureError) as e:
        print(f'[ERROR_TOKEN] Invalid token: {e}')
        return None
    except Exception as e:
        print(f'[ERROR_TOKEN] Unexpected error: {e}')
        return None


def verify_token_and_get_user(token: str) -> Optional[Dict[str, Any]]:
    """Synchronously verify JWT token and get user information."""
    return asyncio.run(_verify_token_and_get_user(token))


async def _change_password(user_id: int, old_password: str, new_password: str) -> Optional[Dict[str, Any]]:
    """Async helper to change user password."""
    async with get_db() as db:
        try:
            # Get user from database
            user = await db.user.find_unique(where={"id": user_id})
            if not user:
                return None
            
            # Verify old password
            if not bcrypt.checkpw(old_password.encode('utf-8'), user.password.encode('utf-8')):
                return None
            
            # Hash new password
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Update password
            updated_user = await db.user.update(
                where={"id": user_id},
                data={"password": hashed_password}
            )
            
            # Return user data without password
            return {
                "id": updated_user.id,
                "email": updated_user.email,
                "role": updated_user.role,
                "name": updated_user.name,
                "status": updated_user.status,
            }
        except Exception as e:
            print(f'[ERROR_CHANGE_PASSWORD] Error changing password: {e}')
            return None


def change_password(user_id: int, old_password: str, new_password: str) -> Optional[Dict[str, Any]]:
    """Synchronously change user password."""
    return asyncio.run(_change_password(user_id, old_password, new_password))