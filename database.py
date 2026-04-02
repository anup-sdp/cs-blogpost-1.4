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
    # as neon can close idle connections after 5 minutes:
    pool_pre_ping=True,   # makes SQLAlchemy test each connection before using it, and automatically reconnects if it's dead.
    pool_recycle=300,     # proactively replaces connections every 5 minutes so they never get old enough for Neon to close them in the first place.
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