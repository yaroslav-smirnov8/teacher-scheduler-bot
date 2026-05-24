"""Migration v8 -> v9: Add homework_attempts table for exercise statistics"""
from sqlalchemy import text, inspect
import logging

logger = logging.getLogger(__name__)


def _table_exists(connection, table_name: str) -> bool:
    try:
        inspector = inspect(connection)
        return table_name in inspector.get_table_names()
    except Exception:
        return False


async def migrate_v8_to_v9(conn) -> None:
    """Create homework_attempts table for tracking student exercise results."""
    try:
        if not _table_exists(conn, 'homework_attempts'):
            await conn.execute(text("""
                CREATE TABLE homework_attempts (
                    id SERIAL PRIMARY KEY,
                    homework_id INTEGER NOT NULL REFERENCES homeworks(id),
                    student_id INTEGER NOT NULL REFERENCES students(id),
                    results VARCHAR(10000) NOT NULL,
                    score INTEGER NOT NULL,
                    total INTEGER NOT NULL,
                    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_homework_attempts_hw
                ON homework_attempts(homework_id, completed_at)
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_homework_attempts_student
                ON homework_attempts(student_id, completed_at)
            """))
            logger.info("Created homework_attempts table")
        else:
            logger.info("homework_attempts table already exists")
    except Exception as e:
        logger.warning(f"Attempts migration note: {e}")
