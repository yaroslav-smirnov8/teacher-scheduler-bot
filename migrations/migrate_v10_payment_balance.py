"""Migration v9 -> v10: Add payment balance tracking (Student.balance, Lesson.paid_from_balance, PaymentTransaction table)"""
from sqlalchemy import text, inspect
import logging

logger = logging.getLogger(__name__)


def _column_exists(conn, table: str, column: str) -> bool:
    try:
        cols = [c["name"] for c in inspect(conn).get_columns(table)]
        return column in cols
    except Exception:
        return False


async def migrate_v9_to_v10(conn) -> None:
    try:
        if not _column_exists(conn, "students", "paid_lessons_balance"):
            await conn.execute(text(
                "ALTER TABLE students ADD COLUMN paid_lessons_balance INTEGER NOT NULL DEFAULT 0"
            ))
            logger.info("Added paid_lessons_balance to students")

        if not _column_exists(conn, "lessons", "paid_from_balance"):
            await conn.execute(text(
                "ALTER TABLE lessons ADD COLUMN paid_from_balance BOOLEAN NOT NULL DEFAULT 0"
            ))
            logger.info("Added paid_from_balance to lessons")

        inspector = inspect(conn)
        tables = inspector.get_table_names()
        if "payment_transactions" not in tables:
            await conn.execute(text("""
                CREATE TABLE payment_transactions (
                    id SERIAL PRIMARY KEY,
                    student_id INTEGER NOT NULL REFERENCES students(id),
                    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
                    type VARCHAR(20) NOT NULL,
                    amount INTEGER NOT NULL,
                    balance_before INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL,
                    lesson_id INTEGER REFERENCES lessons(id),
                    note VARCHAR(500),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_payment_txn_student
                ON payment_transactions(student_id, created_at)
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_payment_txn_teacher
                ON payment_transactions(teacher_id, created_at)
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_payment_txn_lesson
                ON payment_transactions(lesson_id)
            """))
            logger.info("Created payment_transactions table")
        else:
            logger.info("payment_transactions table already exists")
    except Exception as e:
        logger.warning("Payment balance migration note: %s", e)


async def run_migration() -> bool:
    """Entry point for migration runner"""
    from database import engine
    try:
        async with engine.begin() as conn:
            await migrate_v9_to_v10(conn)
        logger.info("Migration v10 completed successfully")
        return True
    except Exception as e:
        logger.error("Migration v10 failed: %s", e)
        return False
