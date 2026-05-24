"""
Migration Script: Add Reschedule Requests System
Executes migration 002_add_reschedule_requests.sql with idempotent handling
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path to import database module
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import engine
from sqlalchemy import text


async def run_migration():
    """Execute the migration with idempotent handling"""
    print("Starting migration: Add Reschedule Requests System")
    print("=" * 60)
    
    async with engine.begin() as conn:
        # Step 1: Create reschedule_requests table
        print("\n[1/2] Creating reschedule_requests table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reschedule_requests (
                id SERIAL PRIMARY KEY,
                lesson_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                teacher_id INTEGER NOT NULL,
                original_date DATE NOT NULL,
                original_time TIME NOT NULL,
                requested_date DATE NOT NULL,
                requested_time TIME NOT NULL,
                reason TEXT NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'declined')),
                created_at DATETIME NOT NULL,
                reviewed_at DATETIME,
                FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
            )
        """))
        print("✓ reschedule_requests table created/verified")
        
        # Step 2: Create indexes
        print("\n[2/2] Creating performance indexes...")
        
        indexes = [
            ("idx_reschedule_requests_student", "reschedule_requests(student_id, created_at)"),
            ("idx_reschedule_requests_teacher", "reschedule_requests(teacher_id, status)"),
            ("idx_reschedule_requests_lesson", "reschedule_requests(lesson_id)")
        ]
        
        for index_name, index_def in indexes:
            await conn.execute(text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}"))
            print(f"  ✓ {index_name}")
        
        # Step 3: Verify migration
        print("\n[3/3] Verifying migration...")
        
        # Check table
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'reschedule_requests'
        """))
        tables = [row[0] for row in result.fetchall()]
        print(f"  ✓ Table created: {', '.join(tables)}")
        
        # Check indexes
        result = await conn.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname = 'public' AND indexname LIKE 'idx_reschedule_%'
            ORDER BY indexname
        """))
        indexes_created = [row[0] for row in result.fetchall()]
        print(f"  ✓ Indexes created: {len(indexes_created)} indexes")
    
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
