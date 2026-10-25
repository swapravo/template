-- [2026-10-24] Initial schema

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT        NOT NULL UNIQUE,
    password_hash TEXT        NOT NULL,
    is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- ---------------------------------------------------------------------------
-- request_logs  (append-only — never UPDATE or DELETE rows in this table)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS request_logs (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    method      TEXT        NOT NULL,
    path        TEXT        NOT NULL,
    status_code INTEGER     NOT NULL,
    duration_ms INTEGER     NOT NULL,
    user_id     UUID        REFERENCES users(id) ON DELETE SET NULL,
    session_id  TEXT,
    ip_address  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_request_logs_created_at ON request_logs (created_at);
CREATE INDEX IF NOT EXISTS idx_request_logs_user_id    ON request_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_request_logs_path       ON request_logs (path);
