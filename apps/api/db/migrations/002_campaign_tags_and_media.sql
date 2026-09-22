-- Migration 002 — Campaign Tags + VIDEO/CAROUSEL Media Metadata (2026-09)
--
-- CREATE TABLE IF NOT EXISTS (in db/schema.sql) does NOT add columns to tables that already
-- exist. This migration is the additive patch for already-deployed databases.
--
-- Safety:
--   - CREATE TABLE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS only (idempotent, safe to re-run)
--   - no DROP TABLE / DROP COLUMN / destructive rename
--   - no existing row is deleted or overwritten
--
-- Apply with (Supabase SQL Editor or psql):
--   psql "$DATABASE_URL" -f apps/api/db/migrations/002_campaign_tags_and_media.sql

-- Campaign Tags — 프로젝트별 사용자 정의 캠페인 분류 태그.
CREATE TABLE IF NOT EXISTS campaign_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    definition TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_campaign_tags_project ON campaign_tags(project_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_campaign_tags_project_name_active
    ON campaign_tags(project_id, lower(name)) WHERE is_active;

-- ads: Campaign Tag 자동 분류 — assignment_source("누가 지정했는가")와 classification_status
-- ("상태")를 분리한다. NEEDS_REVIEW는 상태이지 지정 주체가 아니다.
ALTER TABLE ads ADD COLUMN IF NOT EXISTS campaign_tag_id UUID REFERENCES campaign_tags(id) ON DELETE SET NULL;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS campaign_tag_confidence DOUBLE PRECISION;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS campaign_tag_reason TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS campaign_tag_assignment_source VARCHAR(10); -- 'AI', 'USER', NULL
ALTER TABLE ads ADD COLUMN IF NOT EXISTS campaign_tag_classified_at TIMESTAMPTZ;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS campaign_classification_status VARCHAR(20) NOT NULL DEFAULT 'PENDING';
ALTER TABLE ads ADD COLUMN IF NOT EXISTS campaign_classification_retry_count INT NOT NULL DEFAULT 0;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS campaign_classification_error TEXT;

-- ads: VIDEO/CAROUSEL 미디어 메타데이터 — image_url은 기존과 동일하게 "대표 썸네일 1장"으로 계속
-- 쓰인다. 기존에 수집된 VIDEO 소재는 재수집 시 app.services.ad_sync가 빈 필드만 채운다(백필 스크립트
-- 불필요 — app/services/ad_sync.py의 backfill 로직 참고).
ALTER TABLE ads ADD COLUMN IF NOT EXISTS video_url TEXT;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS media_items JSONB;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS keyframe_urls JSONB;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS keyframe_status VARCHAR(20) NOT NULL DEFAULT 'NOT_APPLICABLE';
ALTER TABLE ads ADD COLUMN IF NOT EXISTS keyframe_retry_count INT NOT NULL DEFAULT 0;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS keyframe_error TEXT;
