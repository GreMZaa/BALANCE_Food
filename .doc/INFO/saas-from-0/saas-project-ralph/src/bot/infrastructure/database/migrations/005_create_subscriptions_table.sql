-- Migration: 005_create_subscriptions_table
-- Description: Create subscriptions table for Telegram Stars payments
-- Created: 2026-01-27

-- Create ENUM type for plan type
DO $$ BEGIN
    CREATE TYPE plan_type_enum AS ENUM ('week', 'month', 'three_months');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Subscriptions table
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_expires_at ON subscriptions(expires_at);
CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(user_id, is_active) WHERE is_active = TRUE;

-- Comments
COMMENT ON TABLE subscriptions IS 'User subscriptions paid via Telegram Stars';
COMMENT ON COLUMN subscriptions.plan_type IS 'Subscription plan: week, month, or three_months';
COMMENT ON COLUMN subscriptions.stars_paid IS 'Number of Telegram Stars paid';
COMMENT ON COLUMN subscriptions.telegram_payment_charge_id IS 'Telegram payment charge ID for refunds';
COMMENT ON COLUMN subscriptions.starts_at IS 'When subscription becomes active';
COMMENT ON COLUMN subscriptions.expires_at IS 'When subscription expires';
COMMENT ON COLUMN subscriptions.is_active IS 'Whether subscription is currently active';
