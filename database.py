"""Database configuration"""
import os
import logging
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from contextlib import asynccontextmanager
from models import Base
from migrations import MIGRATIONS

logger = logging.getLogger(__name__)

load_dotenv()

DB_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/teacherhelper')

SCHEMA_VERSION = 11

engine = create_async_engine(DB_URL, echo=False)

SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_schema_version(conn):
    """Get current schema version from the database.
    
    Returns 0 if no version tracking table exists.
    Uses savepoint to avoid aborting the transaction on PostgreSQL.
    """
    try:
        async with conn.begin_nested():
            result = await conn.execute(text(
                "SELECT version FROM schema_version ORDER BY id DESC LIMIT 1"
            ))
            row = result.fetchone()
            return row[0] if row else 0
    except Exception:
        return 0


async def set_schema_version(conn, version):
    """Set the schema version in the database."""
    await conn.execute(text(
        "CREATE TABLE IF NOT EXISTS schema_version (id SERIAL PRIMARY KEY, version INTEGER NOT NULL)"
    ))
    await conn.execute(text(
        "INSERT INTO schema_version (version) VALUES (:version)"
    ), {"version": version})


async def init_db():
    """Initialize database with automatic migration support.
    
    Creates all tables defined in models.py and applies incremental migrations
    if the schema version is outdated.
    
    The function is idempotent - safe to call multiple times.
    """
    async with engine.begin() as conn:
        # Create/update all tables from models definitions
        await conn.run_sync(Base.metadata.create_all)
        current_version = await get_schema_version(conn)
    
    if current_version < SCHEMA_VERSION:
        logger.info(f"Database schema version {current_version}, target {SCHEMA_VERSION}. Running migrations...")
        
        for version in range(current_version, SCHEMA_VERSION):
            if version in MIGRATIONS:
                logger.info(f"Applying migration v{version} -> v{version + 1}")
                try:
                    async with engine.begin() as conn:
                        await MIGRATIONS[version](conn)
                except Exception as e:
                    logger.warning(f"Migration v{version} skipped: {e}")
        
        async with engine.begin() as conn:
            await set_schema_version(conn, SCHEMA_VERSION)
            logger.info(f"Database migrated to schema version {SCHEMA_VERSION}")


@asynccontextmanager
async def get_session():
    """Context manager for database sessions"""
    session = SessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
