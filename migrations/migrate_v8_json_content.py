"""Migration v7 -> v8: Add json_content column to homeworks table"""
from sqlalchemy import text, inspect
import logging

logger = logging.getLogger(__name__)


def _column_exists(connection, table_name: str, column_name: str) -> bool:
    try:
        inspector = inspect(connection)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


async def migrate_v7_to_v8(conn) -> None:
    """Add json_content column for interactive AI homework exercises."""
    try:
        if not _column_exists(conn, 'homeworks', 'json_content'):
            await conn.execute(text(
                "ALTER TABLE homeworks ADD COLUMN json_content VARCHAR(10000)"
            ))
            logger.info("Added json_content column to homeworks table")
        else:
            logger.info("json_content column already exists")
    except Exception as e:
        logger.warning(f"JSON content migration note: {e}")
