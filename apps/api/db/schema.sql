-- Schema for ADCatcher (PostgreSQL / Supabase)

-- 1. Users Table (Bypassed auth for MVP using default admin)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE DEFAULT 'admin@company.com',
    last_accessed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Insert Default Admin
INSERT INTO users (email) VALUES ('admin@company.com')
ON CONFLICT (email) DO NOTHING;

-- 2. Projects (Workspace) Table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE', -- 'ACTIVE', 'PAUSED'
    -- 새 프로젝트는 명시적 opt-in(Baseline CTA) 전까지 자동 수집하지 않는다.
    -- 기존 row에는 영향 없음 (DEFAULT는 신규 INSERT에만 적용됨).
    auto_collect_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. Competitors Table ("추적 브랜드" — Brand Model Simplification, 2026-09)
CREATE TABLE IF NOT EXISTS competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    ad_library_url TEXT NOT NULL,
    page_id VARCHAR(100),
    -- DEPRECATED: 자사/경쟁사 구분은 더 이상 business logic에서 사용하지 않는다(모든 등록 브랜드를
    -- 동일하게 집계). 기존 데이터 보존을 위해 column만 유지한다.
    is_own_brand BOOLEAN DEFAULT FALSE,
    -- P0-08: "첫 수집"이 아니라 "첫 COMPLETE SUCCESSFUL SNAPSHOT"이 Baseline이다. NULL이면
    -- 아직 baseline 미확정(PARTIAL만 있었거나 수집 이력 없음) — 이 상태에선 STARTED/STOPPED/
    -- REACTIVATED 이벤트를 생성하지 않는다.
    baseline_completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 4. Campaign Tags — 프로젝트별 사용자 정의 캠페인 분류 태그 (additive, 2026-09). 시스템에 고정된
-- 카테고리를 두지 않고, 프로젝트마다 태그명+정의를 자유롭게 관리한다. ads.campaign_tag_id가 이
-- 테이블을 참조하므로 ads보다 먼저 생성한다.
CREATE TABLE IF NOT EXISTS campaign_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    definition TEXT NOT NULL,
    -- 삭제는 soft delete(is_active=FALSE)다 — 과거 소재에 이미 붙은 태그 표시/이력을 보존하기 위해
    -- hard delete를 하지 않는다. 비활성 태그는 Gemini 분류 입력/수동 지정 후보에서 항상 제외된다.
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_campaign_tags_project ON campaign_tags(project_id);
-- 동시 요청 경합 대비 DB 레벨 안전망(주 검증은 app.services.campaign_tags 서비스 레이어에서 수행).
CREATE UNIQUE INDEX IF NOT EXISTS idx_campaign_tags_project_name_active
    ON campaign_tags(project_id, lower(name)) WHERE is_active;

-- 5. Ads Table
CREATE TABLE IF NOT EXISTS ads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_id UUID REFERENCES competitors(id) ON DELETE CASCADE,
    ad_archive_id VARCHAR(100) NOT NULL UNIQUE,
    first_seen_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    -- 소재상의 실제 집행 시작일(모르면 NULL) — ADCatcher가 처음 관측한 first_seen_at과는 별개 개념.
    -- 있으면 "집행 N일", 없으면 "추적 N일"로 표시한다.
    source_started_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'NEW', -- 'NEW', 'ACTIVE', 'INACTIVE'
    visual_type VARCHAR(50), -- 'PERSON', 'PRODUCT', 'TEXT_HEAVY', 'GRAPHIC'
    format VARCHAR(20), -- 'IMAGE', 'VIDEO' (2026-09-23: CAROUSEL 제거 — 마이그레이션은 003_simplify_media_format.sql)
    image_url TEXT,
    copy_text TEXT,
    cta_text VARCHAR(100),
    consecutive_inactive_days INT DEFAULT 0,
    -- PRD 3.3: INACTIVE 전환 후 14일 연속 미노출 시 수집 대상 스케줄러에서 아카이빙 처리.
    is_archived BOOLEAN DEFAULT FALSE,
    -- Gemini/썸네일 캐싱(enrichment)은 수집(core data)과 완전히 분리된 상태로 추적한다 — 분석이
    -- 실패해도 ads row 자체는 항상 정상 생성/유지된다.
    analysis_status VARCHAR(20) DEFAULT 'PENDING', -- 'PENDING', 'SUCCESS', 'FAILED'
    analysis_retry_count INT DEFAULT 0,
    analysis_error TEXT,
    analyzed_at TIMESTAMPTZ,
    -- Campaign Tag 자동 분류 (additive, 2026-09) — assignment_source("누가 지정했는가")와
    -- campaign_classification_status("상태")를 분리한다. NEEDS_REVIEW는 상태이지 지정 주체가 아니다.
    campaign_tag_id UUID REFERENCES campaign_tags(id) ON DELETE SET NULL,
    campaign_tag_confidence DOUBLE PRECISION,
    campaign_tag_reason TEXT,
    campaign_tag_assignment_source VARCHAR(10), -- 'AI', 'USER', NULL(미지정)
    campaign_tag_classified_at TIMESTAMPTZ,
    campaign_classification_status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING|SUCCESS|NEEDS_REVIEW|FAILED
    campaign_classification_retry_count INT NOT NULL DEFAULT 0,
    campaign_classification_error TEXT,
    -- VIDEO 미디어 메타데이터 (additive, 2026-09) — image_url은 기존과 동일하게
    -- "대표 썸네일 1장"으로 계속 쓰인다.
    video_url TEXT, -- VIDEO 포맷 전용 참고용 원본 URL(HD 우선, SD fallback) — UI에서 재생하지 않는다
    -- media_items/keyframe_* : 2026-09-23 ffmpeg keyframe 파이프라인 폐기 + CAROUSEL 제거로
    -- 더 이상 API/서비스에서 쓰지 않는다. 컬럼은 legacy로 남겨둔다(운영 안정화 후 별도
    -- migration으로 drop 검토) — db/migrations/003_simplify_media_format.sql 참고.
    media_items JSONB,
    keyframe_urls JSONB,
    keyframe_status VARCHAR(20) NOT NULL DEFAULT 'NOT_APPLICABLE',
    keyframe_retry_count INT NOT NULL DEFAULT 0,
    keyframe_error TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexing for Query Performance
CREATE INDEX IF NOT EXISTS idx_ads_competitor ON ads(competitor_id);
CREATE INDEX IF NOT EXISTS idx_ads_status ON ads(status);
CREATE INDEX IF NOT EXISTS idx_ads_archive_id ON ads(ad_archive_id);

-- ── Daily Ad Change History (additive, 2026-09) ─────────────────────────
-- ads 테이블은 "현재 상태"만 담당한다. 아래 3개 테이블이 수집 실행 기록 / 관측 증거 /
-- 상태 변화 이력을 각각 분리해서 담당한다. 기존 테이블 컬럼은 변경하지 않는다.

-- 6. Collection Runs — 경쟁사 1곳에 대한 수집 시도 1회 (성공/실패 명시적 기록)
CREATE TABLE IF NOT EXISTS collection_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_id UUID REFERENCES competitors(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    run_date DATE NOT NULL, -- KST(Asia/Seoul) 캘린더 날짜로 시작 시점에 고정
    -- 'PARTIAL' = fetch는 성공했지만 max_ads 상한 도달로 전체 스냅샷을 보장할 수 없음(P0-02).
    -- PARTIAL인 run은 STOPPED 판정이나 baseline 확정에 사용되지 않는다.
    status VARCHAR(20) NOT NULL DEFAULT 'RUNNING', -- 'RUNNING', 'SUCCESS', 'PARTIAL', 'FAILED'
    fetched_ads_count INT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 7. Ad Observations — SUCCESS인 run에서 실제로 발견된 광고 (스냅샷 비교의 근거)
CREATE TABLE IF NOT EXISTS ad_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_run_id UUID REFERENCES collection_runs(id) ON DELETE CASCADE,
    competitor_id UUID REFERENCES competitors(id) ON DELETE CASCADE,
    ad_id UUID REFERENCES ads(id) ON DELETE CASCADE,
    observed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 8. Ad Status Events — 상태 "전환이 발생한 순간"에만 1건 생성 (반복 기록 금지)
-- event_date는 KST(Asia/Seoul) 기준 캘린더 날짜로 고정 저장 (UTC 경계로 하루 밀림 방지)
CREATE TABLE IF NOT EXISTS ad_status_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ad_id UUID REFERENCES ads(id) ON DELETE CASCADE,
    competitor_id UUID REFERENCES competitors(id) ON DELETE CASCADE,
    collection_run_id UUID REFERENCES collection_runs(id) ON DELETE CASCADE,
    event_type VARCHAR(20) NOT NULL, -- 'STARTED', 'STOPPED', 'REACTIVATED', 'BASELINE_DISCOVERED'
    event_date DATE NOT NULL,
    previous_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    -- P1-01: 이벤트 발생 시점에 고정한 집행/추적 일수(historical immutability). 이후 ad row가
    -- 갱신돼도 이 값은 바뀌지 않는다. 이 컬럼 도입 이전 이벤트는 NULL(fake backfill 금지).
    survival_days_at_event INT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_collection_runs_competitor ON collection_runs(competitor_id, run_date, status);
CREATE INDEX IF NOT EXISTS idx_ad_observations_run ON ad_observations(collection_run_id);
CREATE INDEX IF NOT EXISTS idx_ad_observations_competitor_ad ON ad_observations(competitor_id, ad_id);
CREATE INDEX IF NOT EXISTS idx_ad_status_events_competitor_date ON ad_status_events(competitor_id, event_date);
CREATE INDEX IF NOT EXISTS idx_ad_status_events_ad ON ad_status_events(ad_id);