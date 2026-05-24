# Migration 001: Recurring Lessons System - Summary

## Overview
This migration adds support for recurring lessons to the database schema. It introduces two new tables and extends the existing `lessons` table.

## Changes Made

### New Tables

#### 1. `recurring_patterns`
Stores the pattern/template for recurring lessons.

**Columns:**
- `id` - Primary key
- `teacher_id` - Foreign key to teachers table
- `student_id` - Foreign key to students table
- `start_date` - When the recurring pattern starts
- `end_date` - When it ends (NULL = infinite)
- `time` - Time of day for lessons
- `frequency` - Type: 'weekly', 'biweekly', or 'monthly'
- `interval` - Interval multiplier (e.g., every 2 weeks)
- `weekday` - Day of week (0=Monday, 6=Sunday) for weekly patterns
- `day_of_month` - Day of month for monthly patterns
- `created_from_lesson_id` - Optional reference to original lesson

**Constraints:**
- CHECK constraint on frequency (must be 'weekly', 'biweekly', or 'monthly')
- Foreign keys with CASCADE delete for teacher and student
- Foreign key with SET NULL for created_from_lesson_id

#### 2. `recurring_exceptions`
Stores dates when a recurring lesson should NOT occur (cancellations).

**Columns:**
- `id` - Primary key
- `pattern_id` - Foreign key to recurring_patterns
- `exception_date` - Date to skip
- `reason` - Optional text explanation

**Constraints:**
- UNIQUE constraint on (pattern_id, exception_date)
- Foreign key with CASCADE delete for pattern_id

### Modified Tables

#### `lessons`
Added new column:
- `recurring_pattern_id` - Foreign key to recurring_patterns (NULL for one-time lessons)

### Indexes Created

For optimal query performance:

1. `idx_recurring_patterns_teacher` - On (teacher_id, start_date)
   - Fast lookup of patterns by teacher
   
2. `idx_recurring_patterns_student` - On (student_id, start_date)
   - Fast lookup of patterns by student
   
3. `idx_recurring_exceptions_pattern` - On (pattern_id, exception_date)
   - Fast lookup of exceptions for a pattern
   
4. `idx_lessons_pattern` - On (recurring_pattern_id, date)
   - Fast lookup of lesson instances for a pattern

## Performance Impact

### Query Optimization
- Indexes enable O(log n) lookups instead of O(n) table scans
- Composite indexes optimize common query patterns (teacher + date range)

### Memory Usage
- Minimal: Only stores patterns and exceptions, not all future lesson instances
- Lessons are generated "on the fly" when needed

### Storage Requirements
- `recurring_patterns`: ~100 bytes per pattern
- `recurring_exceptions`: ~50 bytes per exception
- `lessons.recurring_pattern_id`: 4 bytes per lesson
- Indexes: ~50-100 bytes per entry

**Example:** 10 teachers with 5 recurring patterns each = ~5KB storage

## Backward Compatibility

✓ **Fully backward compatible**
- Existing lessons continue to work (recurring_pattern_id = NULL)
- No changes to existing data
- All changes are additive only
- No breaking changes to existing queries

## Migration Safety

### Idempotency
All operations are idempotent:
- `CREATE TABLE IF NOT EXISTS`
- `CREATE INDEX IF NOT EXISTS`
- Column existence check before ALTER TABLE

### Rollback
Can be rolled back by:
1. Dropping the two new tables
2. Dropping the four new indexes
3. Removing the column from lessons (requires table recreation in SQLite)

**Warning:** Rollback will delete all recurring lesson data!

## Testing

### Verification Steps
1. Run `python migrations/verify_migration.py`
2. Check that all tables exist
3. Check that all indexes exist
4. Check that foreign keys are configured
5. Verify the new column in lessons table

### Test Cases Covered
- ✓ Fresh database (no existing tables)
- ✓ Existing database with base tables
- ✓ Re-running migration (idempotency)
- ✓ Foreign key constraints
- ✓ CHECK constraints on frequency
- ✓ UNIQUE constraint on exceptions

## Usage Examples

### Creating a Recurring Pattern
```python
pattern = RecurringPattern(
    teacher_id=1,
    student_id=5,
    start_date=date(2024, 1, 8),
    end_date=date(2024, 6, 30),
    time=time(15, 0),
    frequency='weekly',
    interval=1,
    weekday=0  # Monday
)
session.add(pattern)
await session.commit()
```

### Adding an Exception
```python
exception = RecurringException(
    pattern_id=1,
    exception_date=date(2024, 2, 12),
    reason="Teacher vacation"
)
session.add(exception)
await session.commit()
```

### Linking a Lesson to a Pattern
```python
lesson = Lesson(
    date=date(2024, 1, 8),
    time=time(15, 0),
    teacher_id=1,
    student_id=5,
    recurring_pattern_id=1  # Links to pattern
)
session.add(lesson)
await session.commit()
```

## Related Files

- `migrations/001_add_recurring_lessons.sql` - Raw SQL migration
- `migrations/run_migration_001.py` - Python migration script
- `migrations/verify_migration.py` - Verification script
- `migrations/migrate.py` - Migration runner
- `models.py` - SQLAlchemy models (already updated)
- `.kiro/specs/recurring-lessons-system/design.md` - Design document

## Next Steps

After running this migration:
1. Implement `RecurringLessonService` (Task 2.2)
2. Implement `AccessControlService` (Task 2.3)
3. Implement `RecurrenceGenerator` (Task 2.4)
4. Add bot handlers for recurring lessons (Task 3.x)

## Questions?

See `migrations/README.md` for detailed usage instructions.
