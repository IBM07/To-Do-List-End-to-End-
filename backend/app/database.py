# ===========================================
# AuraTask Database Configuration
# ===========================================
# Async MySQL connection with robust connection pooling

from contextlib import contextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import AsyncAdaptedQueuePool, QueuePool

from app.config import settings


# ===========================================
# SQLAlchemy Base for Models
# ===========================================
Base = declarative_base()


# ===========================================
# Async Engine (For FastAPI)
# ===========================================
async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=10,              # Base number of connections
    max_overflow=20,           # Extra connections when pool is full (up to 30 total)
    pool_timeout=30,           # Wait time (seconds) for available connection
    pool_recycle=1800,         # Recycle connections after 30 minutes
    pool_pre_ping=True,        # Verify connection health before use
    echo=settings.DEBUG,       # Log SQL queries in debug mode
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage:
        @router.get("/tasks")
        async def get_tasks(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ===========================================
# Sync Engine (For Celery Workers)
# ===========================================
# Celery workers can't use async, so we need a sync engine
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,               # Smaller pool for workers
    max_overflow=10,           # Up to 15 total connections
    pool_recycle=1800,         # Recycle after 30 minutes
    pool_pre_ping=True,        # Health check before use
    echo=settings.DEBUG,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


@contextmanager
def get_sync_session():
    """
    Context manager for sync sessions in Celery workers.
    
    Usage:
        with get_sync_session() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
    """
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ===========================================
# Database Initialization
# ===========================================
async def init_db():
    """
    Create all tables defined in models.
    Call this on application startup.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    Dispose of the connection pool.
    Call this on application shutdown.
    """
    await async_engine.dispose()
