"""Migration v4 -> v5: Add payment tracking columns"""
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def _column_exists(connection, table_name: str, column_name: str) -> bool:
    try:
        inspector = inspect(connection)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


async def migrate_v4_to_v5(conn) -> None:
    """Add payment tracking columns to lessons and students tables."""
    from sqlalchemy import inspect

    try:
        if not _column_exists(conn, 'lessons', 'is_paid'):
            await conn.execute(text(
                "ALTER TABLE lessons ADD COLUMN is_paid BOOLEAN NOT NULL DEFAULT 0"
            ))
            logger.info("Added is_paid column to lessons table")

        if not _column_exists(conn, 'lessons', 'paid_at'):
            await conn.execute(text(
                "ALTER TABLE lessons ADD COLUMN paid_at TIMESTAMP"
            ))
            logger.info("Added paid_at column to lessons table")

        if not _column_exists(conn, 'lessons', 'paid_by_admin_id'):
            await conn.execute(text(
                "ALTER TABLE lessons ADD COLUMN paid_by_admin_id INTEGER"
            ))
            logger.info("Added paid_by_admin_id column to lessons table")

        if not _column_exists(conn, 'lessons', 'payment_note'):
            await conn.execute(text(
                "ALTER TABLE lessons ADD COLUMN payment_note VARCHAR(500)"
            ))
            logger.info("Added payment_note column to lessons table")

        if not _column_exists(conn, 'lessons', 'payment_reminder_sent_at'):
            await conn.execute(text(
                "ALTER TABLE lessons ADD COLUMN payment_reminder_sent_at TIMESTAMP"
            ))
            logger.info("Added payment_reminder_sent_at column to lessons table")

        if not _column_exists(conn, 'students', 'payment_reminders_enabled'):
            await conn.execute(text(
                "ALTER TABLE students ADD COLUMN payment_reminders_enabled BOOLEAN NOT NULL DEFAULT 0"
            ))
            logger.info("Added payment_reminders_enabled column to students table")

        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_lessons_is_paid ON lessons(is_paid)"
        ))
        logger.info("Created payment tracking indexes")
    except Exception as e:
        logger.warning(f"Payment tracking migration note: {e}")
