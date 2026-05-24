# Quick Start Guide - Database Migrations

## For New Installations

If you're setting up the database for the first time:

```bash
# 1. Initialize the database with base tables
python -c "import asyncio; from database import init_db; asyncio.run(init_db())"

# 2. Run all migrations
python migrations/migrate.py
```

That's it! Your database is ready.

## For Existing Installations

If you already have a database and want to add recurring lessons support:

```bash
# Run the migration runner (it will only apply pending migrations)
python migrations/migrate.py
```

The migration runner tracks which migrations have been applied, so it's safe to run multiple times.

## Verify Everything Works

```bash
python migrations/verify_migration.py
```

You should see:
- ✓ All tables created
- ✓ All indexes created
- ✓ All foreign keys configured
- ✓ Column added to lessons table

## What Was Added?

### New Tables
- `recurring_patterns` - Stores recurring lesson templates
- `recurring_exceptions` - Stores dates when recurring lessons are cancelled

### Modified Tables
- `lessons` - Added `recurring_pattern_id` column (NULL for one-time lessons)

### Performance Indexes
- 4 new indexes for fast queries on recurring lessons

## Next Steps

After running the migration:

1. **Implement Services** (Tasks 2.2-2.4)
   - RecurringLessonService
   - AccessControlService
   - RecurrenceGenerator

2. **Add Bot Handlers** (Tasks 3.x)
   - Create recurring lesson command
   - Convert lesson to recurring
   - Smart delete with choice

3. **Write Tests** (Tasks 4.x)
   - Unit tests for services
   - Property-based tests
   - Integration tests

## Troubleshooting

### "no such table: lessons"
You need to initialize the base database first:
```bash
python -c "import asyncio; from database import init_db; asyncio.run(init_db())"
```

### "column recurring_pattern_id already exists"
This is normal! The migration is idempotent and will skip already-applied changes.

### Want to start fresh?
Delete the database file and re-run initialization:
```bash
rm teacherdb.db
python -c "import asyncio; from database import init_db; asyncio.run(init_db())"
python migrations/migrate.py
```

## Need Help?

- See `README.md` for detailed documentation
- See `MIGRATION_SUMMARY.md` for technical details
- See `.kiro/specs/recurring-lessons-system/design.md` for system design
