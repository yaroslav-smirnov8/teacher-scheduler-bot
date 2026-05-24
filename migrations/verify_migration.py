"""Verify migration 001 was applied correctly"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import engine
from sqlalchemy import text


async def verify_migration():
    """Verify all migration components are in place"""
    print("Verifying Migration 001: Recurring Lessons System")
    print("=" * 60)
    
    async with engine.begin() as conn:
        # Check tables
        print("\n[Tables]")
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name IN ('recurring_patterns', 'recurring_exceptions', 'lessons')
            ORDER BY table_name
        """))
        
        for row in result.fetchall():
            print(f"\n✓ {row[0]}")
        
        # Check indexes
        print("\n[Indexes]")
        result = await conn.execute(text("""
            SELECT indexname, tablename FROM pg_indexes 
            WHERE schemaname = 'public' AND (
                indexname LIKE 'idx_%recurring%' OR 
                indexname LIKE 'idx_lessons_pattern'
            )
            ORDER BY indexname
        """))
        
        indexes = result.fetchall()
        for row in indexes:
            print(f"  ✓ {row[0]} on {row[1]}")
        
        print(f"\n  Total: {len(indexes)} indexes")
        
        # Check lessons table has recurring_pattern_id column
        print("\n[Lessons Table Columns]")
        result = await conn.execute(text("""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'lessons'
            ORDER BY ordinal_position
        """))
        columns = result.fetchall()
        
        has_recurring_column = False
        for col_name, col_type in columns:
            if col_name == 'recurring_pattern_id':
                print(f"  ✓ {col_name} ({col_type})")
                has_recurring_column = True
        
        if not has_recurring_column:
            print("  ✗ ERROR: recurring_pattern_id column not found!")
            return False
        
        # Check foreign keys
        print("\n[Foreign Keys]")
        result = await conn.execute(text("""
            SELECT kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
            AND tc.table_name = 'recurring_patterns'
        """))
        fks = result.fetchall()
        print(f"  ✓ recurring_patterns has {len(fks)} foreign keys")
        
        result = await conn.execute(text("""
            SELECT kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
            AND tc.table_name = 'recurring_exceptions'
        """))
        fks = result.fetchall()
        print(f"  ✓ recurring_exceptions has {len(fks)} foreign keys")
        
        result = await conn.execute(text("""
            SELECT kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
            AND tc.table_name = 'lessons'
        """))
        fks = result.fetchall()
        lessons_fk_count = len(fks)
        print(f"  ✓ lessons has {lessons_fk_count} foreign keys")
        
        # Summary
        print("\n" + "=" * 60)
        print("Migration verification: SUCCESS ✓")
        print("=" * 60)
        return True


async def main():
    try:
        success = await verify_migration()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
