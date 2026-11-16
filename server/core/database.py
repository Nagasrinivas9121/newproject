import datetime
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from server.core.config import settings

def utc_now() -> datetime.datetime:
    """Return timezone-naive UTC timestamp for standard SQL compatibility."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

# Engine setup with appropriate connection arguments based on database dialect
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for yielding transactional async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all registered database tables (used for initial bootstrap & testing)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
