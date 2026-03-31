# database.py:
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from config import settings

# Neon requires ssl — asyncpg handles it via the URL or connect_args
engine = create_async_engine(
    settings.database_url,
    # No connect_args needed for asyncpg (no check_same_thread — that's SQLite-only)
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session