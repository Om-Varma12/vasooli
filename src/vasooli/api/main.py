from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .database import settings
from .deps import engine
from .routes.events import router as events_router
from .routes.system import router as system_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vasooli.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify database connection
    logger.info("Starting up Vasooli API...")
    try:
        # Just a simple connectivity check on startup
        from sqlalchemy import text
        from .deps import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            logger.info("Database connectivity verified.")
    except Exception as e:
        logger.error(f"Database connectivity check failed: {e}")

    yield

    # Shutdown: dispose of the connection pool
    logger.info("Shutting down Vasooli API...")
    await engine.dispose()

app = FastAPI(
    title="Vasooli Recovery API",
    description="API for tracking and managing payment recovery events",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for Frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with actual frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(events_router)
app.include_router(system_router)

@app.get("/debug")
async def debug():
    return {"status": "ok", "message": "The API is actually running and responding!"}

@app.get("/")
async def root():
    return {"message": "Vasooli API is running. Visit /docs for API documentation."}
