-- Migration: Add Reschedule Requests System
-- Description: Adds reschedule_requests table for student lesson reschedule requests
-- Date: 2025-01-17
-- Author: Cascade

-- ============================================================================
-- Table: reschedule_requests
-- ============================================================================

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
);

-- ============================================================================
-- Indexes for performance optimization
-- ============================================================================

-- Index for finding requests by student and creation date (for limit checking)
CREATE INDEX IF NOT EXISTS idx_reschedule_requests_student 
ON reschedule_requests(student_id, created_at);

-- Index for finding pending requests by teacher
CREATE INDEX IF NOT EXISTS idx_reschedule_requests_teacher 
ON reschedule_requests(teacher_id, status);

-- Index for finding requests by lesson
CREATE INDEX IF NOT EXISTS idx_reschedule_requests_lesson 
ON reschedule_requests(lesson_id);

-- ============================================================================
-- Verification queries (optional - for testing)
-- ============================================================================

-- Verify table was created:
-- SELECT name FROM sqlite_master WHERE type='table' AND name='reschedule_requests';

-- Verify indexes were created:
-- SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_reschedule_%';
