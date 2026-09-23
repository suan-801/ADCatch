-- Migration 003 — Simplify media format to IMAGE/VIDEO only (2026-09-23)
--
-- ADCatcher's purpose is a competitor ad tracker ("what's live, what pattern/campaign is it
-- running"), not a video-analysis product. The previous CAROUSEL classification + ffmpeg
-- keyframe pipeline (multi-card structure preservation, video download, 4-frame extraction,
-- Storage upload x4, retry lifecycle) had too many failure points for what the product needs.
-- app.schemas.AdFormat no longer has a CAROUSEL value — this migration downgrades existing
-- CAROUSEL rows to IMAGE so the app-level enum and the stored data stay consistent.
--
-- Safety:
--   - Data-only UPDATE. `ads.format` is a plain VARCHAR(20) (no DB-level enum/CHECK constraint,
--     confirmed in db/schema.sql), so this needs no type-level migration.
--   - Deliberately conservative: blanket CAROUSEL -> IMAGE, no attempt to inspect media_items
--     and "guess" which CAROUSEL rows were actually VIDEO. A row that's genuinely a video ad
--     will be reclassified correctly as VIDEO on its next Apify re-collection by the new
--     2-way classifier (app.services.ad_library_collector.classify_and_extract_media) — that
--     collector call sees the actual raw item, this migration does not. Inspecting media_items
--     here would risk mis-promoting real multi-image carousels that happen to have one video
--     card mixed in (which the new classifier deliberately keeps as IMAGE).
--   - No column is dropped. keyframe_urls/keyframe_status/keyframe_retry_count/keyframe_error/
--     media_items remain in the table as legacy, unused by the app going forward — consider a
--     separate migration to drop them once this is confirmed stable in production.
--
-- Apply with (Supabase SQL Editor or psql):
--   psql "$DATABASE_URL" -f apps/api/db/migrations/003_simplify_media_format.sql

UPDATE ads
SET format = 'IMAGE'
WHERE format = 'CAROUSEL';
