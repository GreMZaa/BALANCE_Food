-- Migration: 003_create_question_sessions_table
-- Description: Create question_sessions table for storing question/answer history
-- Created: 2026-01-27

-- Create ENUM types for category and answer type
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

DO $$ BEGIN
    CREATE TYPE answer_type_enum AS ENUM ('text', 'voice');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Question sessions table
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_question_sessions_user_id ON question_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_question_sessions_created_at ON question_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_question_sessions_user_created ON question_sessions(user_id, created_at DESC);

-- Comments
COMMENT ON TABLE question_sessions IS 'History of all questions and user answers with AI evaluation';
COMMENT ON COLUMN question_sessions.question_text IS 'The interview question text';
COMMENT ON COLUMN question_sessions.question_category IS 'Category of the question (language, algorithms, etc.)';
COMMENT ON COLUMN question_sessions.question_difficulty IS 'Difficulty level 1-10';
COMMENT ON COLUMN question_sessions.user_answer IS 'User answer text (transcribed if voice)';
COMMENT ON COLUMN question_sessions.answer_type IS 'How user answered: text or voice';
COMMENT ON COLUMN question_sessions.ai_score IS 'AI evaluation score 1-10';
COMMENT ON COLUMN question_sessions.ai_feedback IS 'Detailed AI feedback with strengths and improvements';
COMMENT ON COLUMN question_sessions.reference_answer IS 'Example good answer for comparison';
COMMENT ON COLUMN question_sessions.response_time_ms IS 'Time user took to answer in milliseconds';
