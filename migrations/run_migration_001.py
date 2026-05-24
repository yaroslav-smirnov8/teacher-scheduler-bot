"""
Migration Script: Add Recurring Lessons System
Executes migration 001_add_recurring_lessons.sql with idempotent handling
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path to import database module
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import engine
from sqlalchemy import text


async def check_column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    result = await conn.execute(
        text("SELECT COUNT(*) FROM information_schema.columns WHERE table_name = :table_name AND column_name = :column_name"),
        {"table_name": table_name, "column_name": column_name}
    )
    row = result.fetchone()
    return row[0] > 0


async def run_migration():
    """Execute the migration with idempotent handling"""
    print("Starting migration: Add Recurring Lessons System")
    print("=" * 60)
    
    async with engine.begin() as conn:
        # Step 1: Create recurring_patterns table
        print("\n[1/5] Creating recurring_patterns table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS recurring_patterns (
                id SERIAL PRIMARY KEY,
                teacher_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE,
                time TIME NOT NULL,
                frequency VARCHAR(20) NOT NULL CHECK (frequency IN ('weekly', 'biweekly', 'monthly')),
                interval INTEGER NOT NULL DEFAULT 1,
                weekday INTEGER,
                day_of_month INTEGER,
                created_from_lesson_id INTEGER,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (created_from_lesson_id) REFERENCES lessons(id) ON DELETE SET NULL
            )
        """))
        print("✓ recurring_patterns table created/verified")
        
        # Step 2: Create recurring_exceptions table
        print("\n[2/5] Creating recurring_exceptions table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS recurring_exceptions (
                id SERIAL PRIMARY KEY,
                pattern_id INTEGER NOT NULL,
                exception_date DATE NOT NULL,
                reason TEXT,
                FOREIGN KEY (pattern_id) REFERENCES recurring_patterns(id) ON DELETE CASCADE,
                UNIQUE(pattern_id, exception_date)
            )
        """))
        print("✓ recurring_exceptions table created/verified")
        
        # Step 3: Add recurring_pattern_id column to lessons table (idempotent)
        print("\n[3/5] Adding recurring_pattern_id column to lessons table...")
        column_exists = await check_column_exists(conn, 'lessons', 'recurring_pattern_id')
        
        if not column_exists:
            await conn.execute(text("""
                ALTER TABLE lessons 
                ADD COLUMN recurring_pattern_id INTEGER 
                REFERENCES recurring_patterns(id) ON DELETE SET NULL
            """))
            print("✓ Column recurring_pattern_id added to lessons table")
        else:
            print("✓ Column recurring_pattern_id already exists (skipped)")
        
        # Step 4: Create indexes
        print("\n[4/5] Creating performance indexes...")
        
        indexes = [
            ("idx_recurring_patterns_teacher", "recurring_patterns(teacher_id, start_date)"),
            ("idx_recurring_patterns_student", "recurring_patterns(student_id, start_date)"),
            ("idx_recurring_exceptions_pattern", "recurring_exceptions(pattern_id, exception_date)"),
            ("idx_lessons_pattern", "lessons(recurring_pattern_id, date)")
        ]
        
        for index_name, index_def in indexes:
            await conn.execute(text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}"))
            print(f"  ✓ {index_name}")
        
        # Step 5: Verify migration
        print("\n[5/5] Verifying migration...")
        
        # Check tables
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name IN ('recurring_patterns', 'recurring_exceptions')
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        print(f"  ✓ Tables created: {', '.join(tables)}")
        
        # Check indexes
        result = await conn.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname = 'public'
            AND (indexname LIKE 'idx_%%recurring%%' OR indexname = 'idx_lessons_pattern')
            ORDER BY indexname
        """))
        indexes_created = [row[0] for row in result.fetchall()]
        print(f"  ✓ Indexes created: {len(indexes_created)} indexes")
        
        # Check column
        column_exists = await check_column_exists(conn, 'lessons', 'recurring_pattern_id')
        if column_exists:
            print("  ✓ Column recurring_pattern_id exists in lessons table")
        else:
            print("  ✗ ERROR: Column recurring_pattern_id not found!")
            return False
    
    print("\n" + "=" * 60)
    print("Migration completed successfully! ✓")
    print("=" * 60)
    return True


async def main():
    """Main entry point"""
    try:
        success = await run_migration()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
