from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Future is true by default in SQLAlchemy 2.0+
engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for returning a database session."""
    async with AsyncSessionLocal() as session:
        yield session
