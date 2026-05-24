"""Migration v2 -> v3: Add student feedback table indexes"""
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


async def migrate_v2_to_v3(conn) -> None:
    """Create indexes for feedback table."""
    try:
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_feedback_student ON student_feedback(student_id, created_at)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_feedback_read ON student_feedback(is_read, created_at)"
        ))
        logger.info("Created feedback table indexes")
    except Exception as e:
        logger.warning(f"Feedback index creation note: {e}")
