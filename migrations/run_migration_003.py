"""
Migration Script: Add Homeworks System
Executes migration 003_add_homeworks_table.sql with idempotent handling
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


async def check_table_exists(conn, table_name: str) -> bool:
    """Check if a table exists"""
    result = await conn.execute(
        text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = :table_name"),
        {"table_name": table_name}
    )
    row = result.fetchone()
    return row[0] > 0


async def run_migration():
    """Execute the migration with idempotent handling"""
    print("Starting migration: Add Homeworks System")
    print("=" * 60)
    
    async with engine.begin() as conn:
        # Step 1: Create homeworks table
        print("\n[1/6] Creating homeworks table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS homeworks (
                id SERIAL PRIMARY KEY,
                lesson_id INTEGER,
                student_id INTEGER NOT NULL,
                teacher_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                sent_at TIMESTAMP NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'sent',
                
                received_at TIMESTAMP,
                completed_at TIMESTAMP,
                edited_at TIMESTAMP,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE SET NULL,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
                
                CONSTRAINT check_homework_status CHECK (status IN ('sent', 'received', 'completed')),
                UNIQUE(lesson_id)
            )
        """))
        print("✓ homeworks table created/verified")
        
        # Step 2: Add lesson_completed_at column to lessons table
        print("\n[2/6] Adding lesson_completed_at column to lessons table...")
        column_exists = await check_column_exists(conn, 'lessons', 'lesson_completed_at')
        
        if not column_exists:
            await conn.execute(text("""
                ALTER TABLE lessons 
                ADD COLUMN lesson_completed_at TIMESTAMP
            """))
            print("✓ Column lesson_completed_at added to lessons table")
        else:
            print("✓ Column lesson_completed_at already exists (skipped)")
        
        # Step 3: Add homework_prompt_sent_at column to lessons table
        print("\n[3/6] Adding homework_prompt_sent_at column to lessons table...")
        column_exists = await check_column_exists(conn, 'lessons', 'homework_prompt_sent_at')
        
        if not column_exists:
            await conn.execute(text("""
                ALTER TABLE lessons 
                ADD COLUMN homework_prompt_sent_at TIMESTAMP
            """))
            print("✓ Column homework_prompt_sent_at added to lessons table")
        else:
            print("✓ Column homework_prompt_sent_at already exists (skipped)")
        
        # Step 4: Create indexes
        print("\n[4/6] Creating performance indexes...")
        
        indexes = [
            ("idx_homeworks_student_sent", "homeworks(student_id, sent_at DESC)"),
            ("idx_homeworks_teacher_sent", "homeworks(teacher_id, sent_at DESC)"),
            ("idx_homeworks_lesson", "homeworks(lesson_id)"),
            ("idx_homeworks_cleanup", "homeworks(status, created_at)"),
            ("idx_homeworks_sent_status", "homeworks(status, sent_at)"),
            ("idx_lessons_homework_check", "lessons(date, time, homework_prompt_sent_at)"),
        ]
        
        for index_name, index_def in indexes:
            await conn.execute(text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}"))
            print(f"  ✓ {index_name}")
        
        # Step 5: Verify migration
        print("\n[5/6] Verifying migration...")
        
        # Check tables
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'homeworks'
        """))
        tables = result.fetchall()
        print(f"✓ homeworks table verified: {len(tables) > 0}")
        
        # Check columns
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'lessons'
            AND column_name IN ('lesson_completed_at', 'homework_prompt_sent_at')
        """))
        columns = result.fetchall()
        print(f"✓ lessons columns verified: {len(columns)} new columns found")
        
        # Step 6: Update schema version
        print("\n[6/6] Updating schema version...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    id SERIAL PRIMARY KEY, 
                    version INTEGER NOT NULL
                )
            """))
        await conn.execute(text("INSERT INTO schema_version (version) VALUES (4)"))
        print("✓ Schema version updated to 4")
        
        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)


async def main():
    try:
        await run_migration()
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
