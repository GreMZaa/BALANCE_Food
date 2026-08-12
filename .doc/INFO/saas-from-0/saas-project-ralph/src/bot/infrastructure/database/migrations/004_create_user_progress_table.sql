-- Migration: 004_create_user_progress_table
-- Description: Create user_progress table for tracking streak and daily progress
-- Created: 2026-01-27

-- User progress table
CREATE TABLE IF NOT EXISTS user_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_streak INT DEFAULT 0 CHECK (current_streak >= 0),
    longest_streak INT DEFAULT 0 CHECK (longest_streak >= 0),
    total_questions_answered INT DEFAULT 0 CHECK (total_questions_answered >= 0),
    questions_today INT DEFAULT 0 CHECK (questions_today >= 0),
    last_activity_date DATE,
    streak_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_progress UNIQUE (user_id)
);

-- Index for fast lookup by user_id
CREATE INDEX IF NOT EXISTS idx_user_progress_user_id ON user_progress(user_id);

-- Comments
COMMENT ON TABLE user_progress IS 'User streak and daily progress tracking';
COMMENT ON COLUMN user_progress.current_streak IS 'Current consecutive days with daily goal achieved';
COMMENT ON COLUMN user_progress.longest_streak IS 'Best streak ever achieved';
COMMENT ON COLUMN user_progress.total_questions_answered IS 'Total number of questions answered all time';
COMMENT ON COLUMN user_progress.questions_today IS 'Questions answered today (resets at midnight user time)';
COMMENT ON COLUMN user_progress.last_activity_date IS 'Date of last question answered (user timezone)';
COMMENT ON COLUMN user_progress.streak_updated_at IS 'Timestamp when streak was last updated';
