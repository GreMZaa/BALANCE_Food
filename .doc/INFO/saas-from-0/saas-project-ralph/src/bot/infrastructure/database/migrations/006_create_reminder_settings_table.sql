-- Migration: 006_create_reminder_settings_table
-- Description: Create reminder_settings table for notification preferences
-- Created: 2026-01-27

-- Reminder settings table
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

-- Index for fast lookup by user_id
CREATE INDEX IF NOT EXISTS idx_reminder_settings_user_id ON reminder_settings(user_id);

-- Index for finding users who need reminders
CREATE INDEX IF NOT EXISTS idx_reminder_settings_enabled ON reminder_settings(reminders_enabled) WHERE reminders_enabled = TRUE;

-- Trigger to automatically update updated_at
CREATE TRIGGER update_reminder_settings_updated_at
    BEFORE UPDATE ON reminder_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE reminder_settings IS 'User notification preferences for daily reminders';
COMMENT ON COLUMN reminder_settings.reminders_enabled IS 'Whether reminders are enabled for this user';
COMMENT ON COLUMN reminder_settings.reminder_times IS 'Array of times (user local) when reminders should be sent';
COMMENT ON COLUMN reminder_settings.reminders_sent_today IS 'Number of reminders sent today (max 3)';
COMMENT ON COLUMN reminder_settings.last_reminder_date IS 'Date when reminders counter was last reset';
