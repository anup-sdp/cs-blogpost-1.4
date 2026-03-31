from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # changes for async
from sqlalchemy.orm import DeclarativeBase
from config import settings

SQLALCHEMY_DATABASE_URL = settings.database_url # "sqlite+aiosqlite:///./blog.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
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
