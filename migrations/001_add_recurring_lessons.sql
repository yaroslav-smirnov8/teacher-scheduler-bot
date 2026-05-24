-- Migration: Add Recurring Lessons System
-- Description: Adds recurring_patterns and recurring_exceptions tables, 
--              and adds recurring_pattern_id column to lessons table
-- Date: 2024-01-15
-- Author: Kiro

-- ============================================================================
-- Table: recurring_patterns
-- ============================================================================

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
);

-- ============================================================================
-- Table: recurring_exceptions
-- ============================================================================

CREATE TABLE IF NOT EXISTS recurring_exceptions (
    id SERIAL PRIMARY KEY,
    pattern_id INTEGER NOT NULL,
    exception_date DATE NOT NULL,
    reason TEXT,
    FOREIGN KEY (pattern_id) REFERENCES recurring_patterns(id) ON DELETE CASCADE,
    UNIQUE(pattern_id, exception_date)
);

-- ============================================================================
-- Alter existing lessons table
-- ============================================================================

-- Add recurring_pattern_id column if it doesn't exist
-- SQLite doesn't support "ADD COLUMN IF NOT EXISTS", so we need to check first
-- This is handled by the Python migration script

-- For manual execution, check if column exists first:
-- SELECT COUNT(*) FROM pragma_table_info('lessons') WHERE name='recurring_pattern_id';
-- If result is 0, run the following:

-- ALTER TABLE lessons ADD COLUMN recurring_pattern_id INTEGER REFERENCES recurring_patterns(id) ON DELETE SET NULL;

-- ============================================================================
-- Indexes for performance optimization
-- ============================================================================

-- Index for finding patterns by teacher and date range
CREATE INDEX IF NOT EXISTS idx_recurring_patterns_teacher 
ON recurring_patterns(teacher_id, start_date);

-- Index for finding patterns by student and date range
CREATE INDEX IF NOT EXISTS idx_recurring_patterns_student 
ON recurring_patterns(student_id, start_date);

-- Index for finding exceptions by pattern and date
CREATE INDEX IF NOT EXISTS idx_recurring_exceptions_pattern 
ON recurring_exceptions(pattern_id, exception_date);

-- Index for finding lessons by pattern and date
CREATE INDEX IF NOT EXISTS idx_lessons_pattern 
ON lessons(recurring_pattern_id, date);

-- ============================================================================
-- Verification queries (optional - for testing)
-- ============================================================================

-- Verify tables were created:
-- SELECT name FROM sqlite_master WHERE type='table' AND name IN ('recurring_patterns', 'recurring_exceptions');

-- Verify indexes were created:
-- SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';

-- Verify column was added:
-- SELECT name FROM pragma_table_info('lessons') WHERE name='recurring_pattern_id';
