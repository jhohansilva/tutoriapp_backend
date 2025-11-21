import asyncio
import threading
from contextlib import asynccontextmanager
from prisma import Prisma

prisma = Prisma()

# Persistent event loop running in a separate thread
_persistent_loop = None
_loop_thread = None
_loop_lock = threading.Lock()


def get_persistent_loop():
    """Get or create the persistent event loop."""
    global _persistent_loop, _loop_thread
    
    with _loop_lock:
        if _persistent_loop is None or (_persistent_loop.is_closed() if _persistent_loop else True):
            # Create a new event loop in a new thread
            loop_ready = threading.Event()
            
            def run_loop():
                global _persistent_loop
                _persistent_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(_persistent_loop)
                loop_ready.set()
                _persistent_loop.run_forever()
            
            _loop_thread = threading.Thread(target=run_loop, daemon=True)
            _loop_thread.start()
            
            # Wait for loop to be created
            loop_ready.wait(timeout=5.0)
            if _persistent_loop is None:
                raise RuntimeError("Failed to create persistent event loop")
    
    return _persistent_loop


def run_in_persistent_loop(coro):
    """Run a coroutine in the persistent event loop."""
    loop = get_persistent_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


def stop_persistent_loop():
    """Stop the persistent event loop."""
    global _persistent_loop, _loop_thread
    
    with _loop_lock:
        if _persistent_loop is not None and not _persistent_loop.is_closed():
            _persistent_loop.call_soon_threadsafe(_persistent_loop.stop)
            if _loop_thread is not None:
                _loop_thread.join(timeout=2.0)
            _persistent_loop.close()
            _persistent_loop = None
            _loop_thread = None


@asynccontextmanager
async def get_db():
    """Context manager for Prisma database connection.
    
    Note: Prisma should be initialized at application startup.
    This context manager only ensures the connection is available.
    """
    # Verify connection is available, reconnect if lost
    if not prisma.is_connected():
        try:
            await prisma.connect()
        except Exception as e:
            # If connection fails, try to reconnect
            try:
                await prisma.disconnect()
            except Exception:
                pass
            await prisma.connect()
    
    try:
        yield prisma
    except Exception as e:
        # If there's a connection error during query, try to reconnect
        error_str = str(e).lower()
        if any(keyword in error_str for keyword in ["not connected", "connection", "query engine"]):
            try:
                if prisma.is_connected():
                    await prisma.disconnect()
            except Exception:
                pass
            await prisma.connect()
        raise
    # Don't disconnect here - connection is persistent for the app lifetime

