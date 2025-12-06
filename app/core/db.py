"""Database connection and session management."""

from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

# Engine with connection pooling configuration
engine: AsyncEngine = create_async_engine(
    settings.sqlalchemy_database_uri,
    echo=settings.debug,  # Log SQL statements in debug mode
    pool_pre_ping=True,   # Verify connections before using
    pool_size=5,          # Number of connections to keep open
    max_overflow=10,      # Additional connections allowed beyond pool_size
)

# Session factory - sessions are created per-request
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Initialize the database connection pool.
    
    Call this during application startup to verify connectivity.
    """
    async with engine.begin() as conn:
        # Test connectivity by executing a simple query
        await conn.execute(text("SELECT 1"))
    print("✅ Database connection pool initialized")


async def close_db() -> None:
    """Close the database connection pool.
    
    Call this during application shutdown.
    """
    await engine.dispose()
    print("🔌 Database connection pool closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session.
    
    Sessions are automatically closed after the request completes.
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
