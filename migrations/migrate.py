"""
Database Migration Runner
Runs all pending migrations in order
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import engine
from sqlalchemy import text


async def get_migration_version() -> int:
    """Get current migration version from database"""
    async with engine.begin() as conn:
        # Create migrations table if it doesn't exist
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Get latest version
        result = await conn.execute(text(
            "SELECT COALESCE(MAX(version), 0) as version FROM schema_migrations"
        ))
        row = result.fetchone()
        return row[0]


async def record_migration(version: int):
    """Record that a migration was applied"""
    async with engine.begin() as conn:
        await conn.execute(text(
            "INSERT INTO schema_migrations (version) VALUES (:version)"
        ), {"version": version})


async def run_migrations():
    """Run all pending migrations"""
    print("Database Migration Runner")
    print("=" * 60)
    
    # Get current version
    current_version = await get_migration_version()
    print(f"\nCurrent schema version: {current_version}")
    
    # Define available migrations
    migrations = [
        {
            "version": 1,
            "name": "Add Recurring Lessons System",
            "script": "run_migration_001.py"
        },
        {
            "version": 10,
            "name": "Add Payment Balance Tracking",
            "script": "migrate_v10_payment_balance.py"
        }
    ]
    
    # Find pending migrations
    pending = [m for m in migrations if m["version"] > current_version]
    
    if not pending:
        print("\n✓ Database is up to date. No migrations to run.")
        return
    
    print(f"\nFound {len(pending)} pending migration(s):")
    for m in pending:
        print(f"  - Migration {m['version']}: {m['name']}")
    
    # Run each pending migration
    for migration in pending:
        print(f"\n{'=' * 60}")
        print(f"Running Migration {migration['version']}: {migration['name']}")
        print(f"{'=' * 60}")
        
        # Import and run the migration module
        script_path = Path(__file__).parent / migration['script']
        
        # Execute the migration script
        import importlib.util
        spec = importlib.util.spec_from_file_location("migration", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Run the migration
        success = await module.run_migration()
        
        if not success:
            print(f"\n✗ Migration {migration['version']} failed!")
            sys.exit(1)
        
        # Record successful migration
        await record_migration(migration['version'])
        print(f"\n✓ Migration {migration['version']} recorded in schema_migrations")
    
    print(f"\n{'=' * 60}")
    print("All migrations completed successfully! ✓")
    print(f"{'=' * 60}")


async def main():
    try:
        await run_migrations()
    except Exception as e:
        print(f"\n✗ Migration runner failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
