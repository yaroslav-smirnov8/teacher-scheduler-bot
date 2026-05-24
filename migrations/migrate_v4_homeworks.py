"""Migration v3 -> v4: Add homeworks table columns and indexes"""
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


async def migrate_v3_to_v4(conn) -> None:
    """Add lesson tracking columns and homework indexes."""
    try:
        if not _column_exists(conn, 'lessons', 'lesson_completed_at'):
            await conn.execute(text(
                "ALTER TABLE lessons ADD COLUMN lesson_completed_at TIMESTAMP"
            ))
            logger.info("Added lesson_completed_at column to lessons table")

        if not _column_exists(conn, 'lessons', 'homework_prompt_sent_at'):
            await conn.execute(text(
                "ALTER TABLE lessons ADD COLUMN homework_prompt_sent_at TIMESTAMP"
            ))
            logger.info("Added homework_prompt_sent_at column to lessons table")

        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_homeworks_student_sent ON homeworks(student_id, sent_at DESC)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_homeworks_teacher_sent ON homeworks(teacher_id, sent_at DESC)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_homeworks_lesson ON homeworks(lesson_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_homeworks_cleanup ON homeworks(status, created_at)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_homeworks_sent_status ON homeworks(status, sent_at)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_lessons_homework_check ON lessons(date, time, homework_prompt_sent_at)"
        ))
        logger.info("Created homeworks table indexes")
    except Exception as e:
        logger.warning(f"Homeworks migration note: {e}")
