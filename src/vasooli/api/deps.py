from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .database import settings

# Replace psycopg2 style URL with asyncpg if necessary
# Example: postgresql://user:pass@host/db -> postgresql+asyncpg://user:pass@host/db
async_db_url = settings.DATABASE_URL
if async_db_url.startswith("postgresql://"):
    async_db_url = async_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    async_db_url,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db():
    """Dependency for request-scoped database sessions."""
    async with AsyncSessionLocal() as session:
        yield session
