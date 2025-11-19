from contextlib import asynccontextmanager
from prisma import Prisma

prisma = Prisma()


@asynccontextmanager
async def get_db():
    """Context manager for Prisma database connection."""
    if not prisma.is_connected():
        await prisma.connect()
    try:
        yield prisma
    finally:
        await prisma.disconnect()

