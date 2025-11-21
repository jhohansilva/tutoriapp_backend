from flask import Flask
from flask_cors import CORS

from services.db import prisma, get_persistent_loop, run_in_persistent_loop, stop_persistent_loop

_prisma_initialized = False


def init_prisma():
    """Initialize Prisma connection at application startup in the persistent loop."""
    global _prisma_initialized
    if _prisma_initialized:
        return
    
    try:
        # Ensure persistent loop is created
        get_persistent_loop()
        
        # Check if already connected
        if not prisma.is_connected():
            # Connect in the persistent loop
            run_in_persistent_loop(prisma.connect())
            print("[PRISMA] Database connection established in persistent event loop")
        else:
            print("[PRISMA] Database already connected")
        _prisma_initialized = True
    except Exception as e:
        print(f"[PRISMA] Error connecting to database: {e}")
        raise


def close_prisma():
    """Close Prisma connection and stop persistent loop at application shutdown."""
    try:
        if prisma.is_connected():
            run_in_persistent_loop(prisma.disconnect())
            print("[PRISMA] Database connection closed")
    except Exception as e:
        print(f"[PRISMA] Error closing database connection: {e}")
    finally:
        stop_persistent_loop()
        print("[PRISMA] Persistent event loop stopped")


def create_app() -> Flask:
    """Application factory for the Tutoriapp backend."""
    app = Flask(__name__)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from app.routes import init_app as init_routes

    init_routes(app)

    # Initialize Prisma on first request (lazy initialization)
    @app.before_request
    def ensure_prisma_connected():
        if not _prisma_initialized:
            init_prisma()

    # Handle app shutdown
    import atexit
    atexit.register(close_prisma)

    return app


__all__ = ["create_app"]

