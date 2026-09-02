import logging
from sqlalchemy.ext.asyncio import AsyncSession
from .database import settings, get_conn

async def get_health():
    """Check if the database is reachable."""
    try:
        # Using the session dependency would be better, but for health check
        # we want to verify the raw connection pool is working.
        # We use a simple SELECT 1 query.
        from .deps import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
