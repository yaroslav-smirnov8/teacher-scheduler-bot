"""Migration v5 -> v6: Add UNIQUE constraint on (teacher_id, date, time)"""
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


async def migrate_v5_to_v6(conn) -> None:
    """Remove duplicate lessons and create unique constraint."""
    try:
        await conn.execute(text("""
            DELETE FROM lessons WHERE id NOT IN (
                SELECT MAX(id) FROM lessons
                GROUP BY teacher_id, date, time
            )
        """))
        logger.info("Removed duplicate lessons for UNIQUE constraint")

        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_lesson_teacher_date_time ON lessons(teacher_id, date, time)"
        ))
        logger.info("Created UNIQUE constraint on lessons(teacher_id, date, time)")
    except Exception as e:
        logger.warning(f"UNIQUE constraint migration note: {e}")
