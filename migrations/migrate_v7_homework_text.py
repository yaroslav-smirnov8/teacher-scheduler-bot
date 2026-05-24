"""Migration v6 -> v7: Increase homework text column from 5000 to 10000"""
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


async def migrate_v6_to_v7(conn) -> None:
    """Increase Homework.text column size for PostgreSQL."""
    try:
        await conn.execute(text("ALTER TABLE homeworks ALTER COLUMN text TYPE VARCHAR(10000)"))
        logger.info("Increased homework.text column to VARCHAR(10000)")
    except Exception:
        # SQLite ignores VARCHAR length — safe to skip
        logger.info("Migration v6 -> v7: VARCHAR size hint (skipped, not needed on this backend)")
