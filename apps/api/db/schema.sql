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