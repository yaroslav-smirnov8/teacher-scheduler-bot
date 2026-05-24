"""Migration v1 -> v2: Add recurring lesson tables and indexes"""
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


async def migrate_v1_to_v2(conn) -> None:
    """Add recurring_pattern_id to lessons, create indexes for recurring tables."""
    try:
        await conn.execute(text(
            "ALTER TABLE lessons ADD COLUMN recurring_pattern_id INTEGER REFERENCES recurring_patterns(id)"
        ))
        logger.info("Added recurring_pattern_id column to lessons table")
    except Exception:
        pass

    try:
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_recurring_patterns_teacher ON recurring_patterns(teacher_id, start_date)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_recurring_patterns_student ON recurring_patterns(student_id, start_date)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_recurring_exceptions_pattern ON recurring_exceptions(pattern_id, exception_date)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_lessons_pattern ON lessons(recurring_pattern_id, date)"
        ))
        logger.info("Created performance indexes for recurring lessons")
    except Exception as e:
        logger.warning(f"Index creation note: {e}")
