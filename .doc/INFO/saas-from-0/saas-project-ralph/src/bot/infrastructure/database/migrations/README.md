# Database Migrations

This directory contains SQL migration files for the Interview Trainer Bot database.

## Files

| File | Description |
|------|-------------|
| `000_full_schema.sql` | Complete schema in one file (for fresh setup) |
| `001_create_users_table.sql` | Users table with Telegram data |
| `002_create_user_profiles_table.sql` | User profiles with interview settings |
| `003_create_question_sessions_table.sql` | Question/answer history |
| `004_create_user_progress_table.sql` | Streak and progress tracking |
| `005_create_subscriptions_table.sql` | Telegram Stars subscriptions |
| `006_create_reminder_settings_table.sql` | Notification settings |

## How to Apply

### Option 1: Full Schema (Fresh Database)

Run `000_full_schema.sql` in Supabase SQL Editor:

1. Go to Supabase Dashboard → SQL Editor
2. Copy contents of `000_full_schema.sql`
3. Click "Run"

### Option 2: Individual Migrations

Run each migration in order (001, 002, 003, etc.) in Supabase SQL Editor.

## Schema Overview

```
users
  ├── user_profiles (1:1)
  ├── question_sessions (1:N)
  ├── user_progress (1:1)
  ├── subscriptions (1:N)
  └── reminder_settings (1:1)
```

## ENUM Types

- `specialty_enum`: backend, frontend, qa, devops, data_science
- `grade_enum`: junior, middle, senior
- `category_enum`: language, algorithms, databases, api_design, system_design, architecture, microservices, devops
- `answer_type_enum`: text, voice
- `plan_type_enum`: week, month, three_months

## Indexes

All foreign keys and frequently queried columns have indexes:

- `idx_users_telegram_id` - Fast user lookup by Telegram ID
- `idx_user_profiles_user_id` - Profile lookup by user
- `idx_question_sessions_user_id` - Session history by user
- `idx_question_sessions_created_at` - Recent sessions
- `idx_question_sessions_user_created` - User sessions sorted by date
- `idx_user_progress_user_id` - Progress lookup
- `idx_subscriptions_user_id` - Subscriptions by user
- `idx_subscriptions_expires_at` - Expiring subscriptions
- `idx_subscriptions_active` - Active subscriptions (partial index)
- `idx_reminder_settings_user_id` - Reminder settings lookup
- `idx_reminder_settings_enabled` - Users with reminders enabled (partial index)

## Triggers

- `update_users_updated_at` - Auto-update `updated_at` on users
- `update_user_profiles_updated_at` - Auto-update `updated_at` on profiles
- `update_reminder_settings_updated_at` - Auto-update `updated_at` on reminder_settings
