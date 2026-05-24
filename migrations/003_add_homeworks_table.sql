-- Migration: Add Homeworks System
-- Description: Adds homeworks table for tracking homework sent to students,
--              and adds tracking columns to lessons table for homework prompts
-- Date: 2026-05-18
-- Author: Kiro

-- ============================================================================
-- Table: homeworks
-- ============================================================================

CREATE TABLE IF NOT EXISTS homeworks (
    id SERIAL PRIMARY KEY,
    lesson_id INTEGER,                          -- FK to lessons (can be NULL for independent hw)
    student_id INTEGER NOT NULL,                -- FK to students
    teacher_id INTEGER NOT NULL,                -- FK to teachers
    text TEXT NOT NULL,                         -- Homework content (text only, no attachments)
    sent_at TIMESTAMP NOT NULL,                 -- When homework was sent to student
    status VARCHAR(20) NOT NULL DEFAULT 'sent', -- sent | received | completed
    
    received_at TIMESTAMP,                      -- When student marked as received
    completed_at TIMESTAMP,                     -- When student marked as completed
    
    edited_at TIMESTAMP,                        -- Last edit timestamp (teacher edit tracking)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE SET NULL,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
    
    CONSTRAINT check_homework_status CHECK (status IN ('sent', 'received', 'completed')),
    UNIQUE(lesson_id)  -- One homework per lesson, but multiple independent homeworks per student allowed
);

-- ============================================================================
-- Alter existing lessons table
-- ============================================================================

-- Add homework tracking columns to lessons table
-- SQLite doesn't support "ADD COLUMN IF NOT EXISTS", so we need to check first
-- This is handled by the Python migration script

-- For manual execution, check if columns exist first and add if needed:
-- ALTER TABLE lessons ADD COLUMN lesson_completed_at TIMESTAMP;
-- ALTER TABLE lessons ADD COLUMN homework_prompt_sent_at TIMESTAMP;

-- ============================================================================
-- Indexes for performance optimization
-- ============================================================================

-- Index for finding student homework history (ordered by date)
CREATE INDEX IF NOT EXISTS idx_homeworks_student_sent 
ON homeworks(student_id, sent_at DESC);

-- Index for finding teacher homework history
CREATE INDEX IF NOT EXISTS idx_homeworks_teacher_sent 
ON homeworks(teacher_id, sent_at DESC);

-- Index for lesson-linked homework lookup
CREATE INDEX IF NOT EXISTS idx_homeworks_lesson 
ON homeworks(lesson_id);

-- Index for finding old homework for cleanup (status + date)
CREATE INDEX IF NOT EXISTS idx_homeworks_cleanup 
ON homeworks(status, created_at);

-- Index for finding unclaimed homework
CREATE INDEX IF NOT EXISTS idx_homeworks_sent_status 
ON homeworks(status, sent_at) WHERE status = 'sent';

-- Index for lessons homework detection (find lessons needing prompt)
CREATE INDEX IF NOT EXISTS idx_lessons_homework_check 
ON lessons(date, time, homework_prompt_sent_at);

-- ============================================================================
-- Verification queries (optional - for testing)
-- ============================================================================

-- Verify table was created:
-- SELECT name FROM sqlite_master WHERE type='table' AND name='homeworks';

-- Verify indexes were created:
-- SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_homeworks%';

-- Verify columns were added to lessons:
-- SELECT name FROM pragma_table_info('lessons') WHERE name IN ('lesson_completed_at', 'homework_prompt_sent_at');
