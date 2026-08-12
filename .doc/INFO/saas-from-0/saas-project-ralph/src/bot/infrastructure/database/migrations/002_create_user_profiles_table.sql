-- Migration: 002_create_user_profiles_table
-- Description: Create user_profiles table for storing interview preparation settings
-- Created: 2026-01-27

-- Create ENUM types for specialty and grade
DO $$ BEGIN
    CREATE TYPE specialty_enum AS ENUM ('backend', 'frontend', 'qa', 'devops', 'data_science');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE grade_enum AS ENUM ('junior', 'middle', 'senior');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- User profiles table
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

-- Index for fast lookup by user_id
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

-- Trigger to automatically update updated_at
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE user_profiles IS 'User interview preparation profiles with settings';
COMMENT ON COLUMN user_profiles.specialty IS 'Development specialty (backend only in MVP)';
COMMENT ON COLUMN user_profiles.grade IS 'Developer experience level';
COMMENT ON COLUMN user_profiles.tech_stack IS 'Array of technologies: python, java, go, nodejs, etc.';
COMMENT ON COLUMN user_profiles.focus_areas IS 'Array of focus areas: algorithms, databases, system_design, etc.';
COMMENT ON COLUMN user_profiles.current_difficulty IS 'Current question difficulty level (1-10), adjusted adaptively';
