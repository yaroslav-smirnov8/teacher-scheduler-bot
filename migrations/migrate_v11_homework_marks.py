"""Migration v10 -> v11: Add teacher_mark and optional_done columns to homeworks"""
from sqlalchemy import text, inspect
import logging

logger = logging.getLogger(__name__)


def _column_exists(conn, table: str, column: str) -> bool:
    try:
        cols = [c["name"] for c in inspect(conn).get_columns(table)]
        return column in cols
    except Exception:
        return False


async def migrate_v10_to_v11(conn) -> None:
    try:
        if not _column_exists(conn, "homeworks", "teacher_mark"):
            await conn.execute(text(
                "ALTER TABLE homeworks ADD COLUMN teacher_mark VARCHAR(30)"
            ))
            logger.info("Added teacher_mark to homeworks")

        if not _column_exists(conn, "homeworks", "optional_done"):
            await conn.execute(text(
                "ALTER TABLE homeworks ADD COLUMN optional_done BOOLEAN NOT NULL DEFAULT 0"
            ))
            logger.info("Added optional_done to homeworks")
    except Exception as e:
        logger.warning("Homework marks migration note: %s", e)


async def run_migration() -> bool:
    """Entry point for migration runner"""
    from database import engine
    try:
        async with engine.begin() as conn:
            await migrate_v10_to_v11(conn)
        logger.info("Migration v11 completed successfully")
        return True
    except Exception as e:
        logger.error("Migration v11 failed: %s", e)
        return False
