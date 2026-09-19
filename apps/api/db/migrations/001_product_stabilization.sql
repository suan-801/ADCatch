-- Migration 001 — Product Stabilization + Brand Model Simplification (2026-09)
--
-- CREATE TABLE IF NOT EXISTS (in db/schema.sql) does NOT add columns to tables that already
-- exist. Running schema.sql again against an existing Supabase database will NOT bring it up
-- to date on its own — this migration is the additive patch for already-deployed databases.
--
-- Safety:
--   - every statement is ADD COLUMN IF NOT EXISTS (idempotent, safe to re-run)
--   - no DROP TABLE / DROP COLUMN / destructive rename
--   - no existing row is deleted or overwritten
--
-- Apply with (Supabase SQL Editor or psql):
--   psql "$DATABASE_URL" -f apps/api/db/migrations/001_product_stabilization.sql

-- ads: enrichment (Gemini/thumbnail) tracking + source-side execution date, kept separate
-- from collection core data (P0-07 / P0-11).
ALTER TABLE ads ADD COLUMN IF NOT EXISTS source_started_at TIMESTAMPTZ;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS analysis_status VARCHAR(20) DEFAULT 'PENDING';
ALTER TABLE ads ADD COLUMN IF NOT EXISTS analysis_retry_count INT DEFAULT 0;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS analysis_error TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMPTZ;

-- competitors: explicit baseline state (P0-08) — replaces inferring baseline from
-- collection_runs history alone.
ALTER TABLE competitors ADD COLUMN IF NOT EXISTS baseline_completed_at TIMESTAMPTZ;

-- collection_runs: PARTIAL status (P0-02). Existing CHECK-less VARCHAR column already accepts
-- the new value with no DDL change; this line is a no-op documentation marker.
-- (status VARCHAR(20) already has no CHECK constraint restricting allowed values.)

-- ad_status_events: BASELINE_DISCOVERED event_type (P0-03) is a VARCHAR value, no DDL needed.
-- survival_days_at_event snapshot column (P1-01 — historical immutability of past event cards).
ALTER TABLE ad_status_events ADD COLUMN IF NOT EXISTS survival_days_at_event INT;

-- NOTE: is_own_brand on competitors is intentionally left in place (deprecated, unused by new
-- business logic) rather than dropped — see docs/DATA_SEMANTICS.md and P0-19.
