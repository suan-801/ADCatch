-- Schema for AdCatch (PostgreSQL / Supabase)

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
    auto_collect_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. Competitors Table
CREATE TABLE IF NOT EXISTS competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    ad_library_url TEXT NOT NULL,
    page_id VARCHAR(100),
    -- PRD 3.1: 프로젝트(워크스페이스) = 자사 1 + 경쟁사 N. 자사도 동일 테이블의 row로 등록하되
    -- 대시보드 신규/종료 카운트·갤러리 집계에서는 제외한다.
    is_own_brand BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 4. Ads Table
CREATE TABLE IF NOT EXISTS ads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_id UUID REFERENCES competitors(id) ON DELETE CASCADE,
    ad_archive_id VARCHAR(100) NOT NULL UNIQUE,
    first_seen_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'NEW', -- 'NEW', 'ACTIVE', 'INACTIVE'
    visual_type VARCHAR(50), -- 'PERSON', 'PRODUCT', 'TEXT_HEAVY', 'GRAPHIC'
    format VARCHAR(20), -- 'IMAGE', 'VIDEO', 'CAROUSEL'
    image_url TEXT,
    copy_text TEXT,
    cta_text VARCHAR(100),
    consecutive_inactive_days INT DEFAULT 0,
    -- PRD 3.3: INACTIVE 전환 후 14일 연속 미노출 시 수집 대상 스케줄러에서 아카이빙 처리.
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexing for Query Performance
CREATE INDEX IF NOT EXISTS idx_ads_competitor ON ads(competitor_id);
CREATE INDEX IF NOT EXISTS idx_ads_status ON ads(status);
CREATE INDEX IF NOT EXISTS idx_ads_archive_id ON ads(ad_archive_id);

-- ── Daily Ad Change History (additive, 2026-09) ─────────────────────────
-- ads 테이블은 "현재 상태"만 담당한다. 아래 3개 테이블이 수집 실행 기록 / 관측 증거 /
-- 상태 변화 이력을 각각 분리해서 담당한다. 기존 테이블 컬럼은 변경하지 않는다.

-- 5. Collection Runs — 경쟁사 1곳에 대한 수집 시도 1회 (성공/실패 명시적 기록)
CREATE TABLE IF NOT EXISTS collection_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_id UUID REFERENCES competitors(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    run_date DATE NOT NULL, -- KST(Asia/Seoul) 캘린더 날짜로 시작 시점에 고정
    status VARCHAR(20) NOT NULL DEFAULT 'RUNNING', -- 'RUNNING', 'SUCCESS', 'FAILED'
    fetched_ads_count INT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 6. Ad Observations — SUCCESS인 run에서 실제로 발견된 광고 (스냅샷 비교의 근거)
CREATE TABLE IF NOT EXISTS ad_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_run_id UUID REFERENCES collection_runs(id) ON DELETE CASCADE,
    competitor_id UUID REFERENCES competitors(id) ON DELETE CASCADE,
    ad_id UUID REFERENCES ads(id) ON DELETE CASCADE,
    observed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 7. Ad Status Events — 상태 "전환이 발생한 순간"에만 1건 생성 (반복 기록 금지)
-- event_date는 KST(Asia/Seoul) 기준 캘린더 날짜로 고정 저장 (UTC 경계로 하루 밀림 방지)
CREATE TABLE IF NOT EXISTS ad_status_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ad_id UUID REFERENCES ads(id) ON DELETE CASCADE,
    competitor_id UUID REFERENCES competitors(id) ON DELETE CASCADE,
    collection_run_id UUID REFERENCES collection_runs(id) ON DELETE CASCADE,
    event_type VARCHAR(20) NOT NULL, -- 'STARTED', 'STOPPED', 'REACTIVATED'
    event_date DATE NOT NULL,
    previous_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_collection_runs_competitor ON collection_runs(competitor_id, run_date, status);
CREATE INDEX IF NOT EXISTS idx_ad_observations_run ON ad_observations(collection_run_id);
CREATE INDEX IF NOT EXISTS idx_ad_observations_competitor_ad ON ad_observations(competitor_id, ad_id);
CREATE INDEX IF NOT EXISTS idx_ad_status_events_competitor_date ON ad_status_events(competitor_id, event_date);
CREATE INDEX IF NOT EXISTS idx_ad_status_events_ad ON ad_status_events(ad_id);