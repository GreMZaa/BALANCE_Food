-- Full Database Schema for Interview Trainer Bot
-- This file combines all migrations for initial database setup
-- Version: 1.0
-- Created: 2026-01-27

-- ============================================
-- Helper Functions
-- ============================================

-- Function to automatically update updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================
-- ENUM Types
-- ============================================

-- Specialty enum
DO $$ BEGIN
    CREATE TYPE specialty_enum AS ENUM ('backend', 'frontend', 'qa', 'devops', 'data_science');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Grade enum
DO $$ BEGIN
    CREATE TYPE grade_enum AS ENUM ('junior', 'middle', 'senior');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Question category enum
DO $$ BEGIN
    CREATE TYPE category_enum AS ENUM (
        'language',
        'algorithms',
        'databases',
        'api_design',
        'system_design',
        'architecture',
        'microservices',
        'devops'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Answer type enum
DO $$ BEGIN
    CREATE TYPE answer_type_enum AS ENUM ('text', 'voice');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Plan type enum
DO $$ BEGIN
    CREATE TYPE plan_type_enum AS ENUM ('week', 'month', 'three_months');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================
-- Table: users
-- ============================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10) DEFAULT 'ru',
    timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE users IS 'Telegram users registered in the interview trainer bot';

-- ============================================
-- Table: user_profiles
-- ============================================

CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    specialty specialty_enum NOT NULL DEFAULT 'backend',
    grade grade_enum NOT NULL DEFAULT 'junior',
    tech_stack TEXT[] DEFAULT '{}',
    focus_areas TEXT[] DEFAULT '{}',
    current_difficulty INT DEFAULT 3 CHECK (current_difficulty >= 1 AND current_difficulty <= 10),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_profile UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE user_profiles IS 'User interview preparation profiles with settings';

-- ============================================
-- Table: question_sessions
-- ============================================

CREATE TABLE IF NOT EXISTS question_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_category category_enum,
    question_difficulty INT CHECK (question_difficulty >= 1 AND question_difficulty <= 10),
    user_answer TEXT,
    answer_type answer_type_enum DEFAULT 'text',
    ai_score INT CHECK (ai_score >= 1 AND ai_score <= 10),
    ai_feedback TEXT,
    reference_answer TEXT,
    response_time_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_question_sessions_user_id ON question_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_question_sessions_created_at ON question_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_question_sessions_user_created ON question_sessions(user_id, created_at DESC);

COMMENT ON TABLE question_sessions IS 'History of all questions and user answers with AI evaluation';

-- ============================================
-- Table: user_progress
-- ============================================

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

CREATE INDEX IF NOT EXISTS idx_user_progress_user_id ON user_progress(user_id);

COMMENT ON TABLE user_progress IS 'User streak and daily progress tracking';

-- ============================================
-- Table: subscriptions
-- ============================================

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_type plan_type_enum NOT NULL,
    stars_paid INT NOT NULL CHECK (stars_paid > 0),
    telegram_payment_charge_id VARCHAR(255) UNIQUE,
    starts_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_expires_at ON subscriptions(expires_at);
CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(user_id, is_active) WHERE is_active = TRUE;

COMMENT ON TABLE subscriptions IS 'User subscriptions paid via Telegram Stars';

-- ============================================
-- Table: reminder_settings
-- ============================================

CREATE TABLE IF NOT EXISTS reminder_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reminders_enabled BOOLEAN DEFAULT TRUE,
    reminder_times TIME[] DEFAULT ARRAY['10:00', '15:00', '20:00']::TIME[],
    reminders_sent_today INT DEFAULT 0 CHECK (reminders_sent_today >= 0),
    last_reminder_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_reminder_settings UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_reminder_settings_user_id ON reminder_settings(user_id);
CREATE INDEX IF NOT EXISTS idx_reminder_settings_enabled ON reminder_settings(reminders_enabled) WHERE reminders_enabled = TRUE;

CREATE TRIGGER update_reminder_settings_updated_at
    BEFORE UPDATE ON reminder_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE reminder_settings IS 'User notification preferences for daily reminders';

-- ============================================
-- Summary
-- ============================================
-- Tables created:
--   1. users - Telegram user data
--   2. user_profiles - Interview preparation settings
--   3. question_sessions - Question/answer history
--   4. user_progress - Streak and progress tracking
--   5. subscriptions - Telegram Stars payments
--   6. reminder_settings - Notification preferences
--
-- Indexes created for all foreign keys and frequent queries
-- Triggers for automatic updated_at timestamp updates
-- ENUM types for type safety
