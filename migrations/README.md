# Database Migrations

This directory contains SQL migrations for the recurring lessons system.

## Migration Files

### 001_add_recurring_lessons.sql
Adds the recurring lessons system to the database:
- Creates `recurring_patterns` table
- Creates `recurring_exceptions` table  
- Adds `recurring_pattern_id` column to `lessons` table
- Creates performance indexes

### run_migration_001.py
Python script to execute migration 001 with idempotent handling.

## Running Migrations

### Option 1: Using Migration Runner (Recommended)

The migration runner automatically runs all pending migrations:

```bash
python migrations/migrate.py
```

**Features:**
- ✓ Tracks which migrations have been applied
- ✓ Runs only pending migrations
- ✓ Records migration history in `schema_migrations` table
- ✓ Safe to run multiple times

### Option 2: Using Individual Migration Script

Run a specific migration directly:

```bash
python migrations/run_migration_001.py
```

**Features:**
- ✓ Idempotent (safe to run multiple times)
- ✓ Checks if column already exists before adding
- ✓ Verifies migration success
- ✓ Uses existing database connection from `database.py`

### Option 3: Manual SQL Execution

If you prefer to run SQL directly:

```bash
sqlite3 teacherdb.db < migrations/001_add_recurring_lessons.sql
```

**Note:** You'll need to manually handle the `ALTER TABLE` statement for the `recurring_pattern_id` column. Check if it exists first:

```sql
SELECT COUNT(*) FROM pragma_table_info('lessons') WHERE name='recurring_pattern_id';
```

If the result is 0, run:

```sql
ALTER TABLE lessons ADD COLUMN recurring_pattern_id INTEGER REFERENCES recurring_patterns(id) ON DELETE SET NULL;
```

## Migration Safety

All migrations are designed to be **idempotent**:
- Tables use `CREATE TABLE IF NOT EXISTS`
- Indexes use `CREATE INDEX IF NOT EXISTS`
- Column additions check for existence first (in Python script)

This means you can safely run migrations multiple times without errors.

## Verification

After running a migration, verify it succeeded:

```bash
python migrations/verify_migration.py
```

This will check:
- All required tables exist
- All indexes are created
- Foreign keys are properly configured
- The `recurring_pattern_id` column was added to `lessons`

You can also verify manually using SQL:

```bash
# Check tables were created
sqlite3 teacherdb.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%recurring%';"

# Check indexes were created
sqlite3 teacherdb.db "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%recurring%';"

# Check column was added
sqlite3 teacherdb.db "SELECT name FROM pragma_table_info('lessons') WHERE name='recurring_pattern_id';"
```

## Rollback

To rollback migration 001:

```sql
-- Drop indexes
DROP INDEX IF EXISTS idx_recurring_patterns_teacher;
DROP INDEX IF EXISTS idx_recurring_patterns_student;
DROP INDEX IF EXISTS idx_recurring_exceptions_pattern;
DROP INDEX IF EXISTS idx_lessons_pattern;

-- Drop tables (cascade will handle foreign keys)
DROP TABLE IF EXISTS recurring_exceptions;
DROP TABLE IF EXISTS recurring_patterns;

-- Remove column from lessons (requires table recreation in SQLite)
-- This is complex in SQLite - backup data first!
```

**Warning:** Rollback will delete all recurring lesson data. Only use in development.

## Future Migrations

When adding new migrations:
1. Create a new SQL file: `00X_description.sql`
2. Create a corresponding Python script: `run_migration_00X.py`
3. Update this README with the new migration details
4. Ensure idempotent design (safe to run multiple times)
