from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:password@localhost:5432/adcatch"

    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_storage_bucket: str = "ad-thumbnails"

    apify_token: str = ""
    apify_actor: str = "curious_coder/facebook-ads-library-scraper"
    # 한 번의 수집으로 가져올 광고 수 상한. 도달 시 스냅샷이 잘렸을 수 있다고 간주해
    # PARTIAL로 표시하고 STOPPED 판정을 건너뛴다 (P0-02). 대부분의 광고주는 이 값보다
    # 훨씬 적은 라이브 소재를 운영하므로, 실질적으로는 "전체 수집"과 동일하게 동작한다.
    apify_max_ads: int = 500

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    # 신규 소재 enrichment(이미지 다운로드+Storage 캐싱+Gemini 태깅)를 동시에 몇 개까지 처리할지.
    # 순차 처리 시 광고 수가 많은 브랜드는 수집 1회에 수 분~수십 분이 걸릴 수 있어 병렬화했다.
    media_enrichment_concurrency: int = 8

    # Part A — Gemini Pending Analysis Retry. 한 번의 재시도 배치에서 처리할 PENDING 소재 상한
    # (Gemini Free Tier RPD는 모델/계정마다 다르므로 하드코딩하지 않고 여기서만 조정한다).
    gemini_pending_batch_size: int = 20
    # 이 횟수만큼 재시도해도 계속 실패하면(quota 제외) analysis_status=FAILED로 확정한다.
    gemini_analysis_max_retries: int = 3

    teams_webhook_url: str = ""

    default_admin_email: str = "admin@company.com"

    auto_pause_days: int = 14
    archive_after_inactive_days: int = 14

    # 콤마로 구분된 허용 프론트엔드 origin 목록 (P0-11). 운영 배포 시 .env에서
    # CORS_ALLOWED_ORIGINS=https://app.adcatcher.com,https://staging.adcatcher.com 형태로 지정.
    cors_allowed_origins: str = "http://localhost:3000"

    # ── Viewer/Admin 권한 ──────────────────────────────────────────────
    # 사용자 계정 시스템이 아니라 "공용 Viewer + 공용 Admin" MVP 구조 (PRD 확장).
    # 원본 비밀번호는 저장하지 않는다 — bcrypt hash만 보관 (scripts/hash_admin_password.py로 생성).
    admin_password_hash: str = ""
    # 세션 쿠키 서명용 비밀키. 비어 있으면 어떤 세션 토큰도 유효하지 않은 것으로 취급한다
    # (=Admin 기능이 비활성화된 안전한 기본값).
    admin_session_secret: str = ""
    admin_session_ttl_hours: int = 8
    # 로컬 개발(frontend/backend가 같은 site인 localhost)은 "lax"로 충분하다. Vercel 등으로
    # frontend/backend 도메인이 분리되는 운영 배포에서는 "none"+Secure=true가 필요하다.
    admin_cookie_samesite: str = "lax"
    admin_cookie_secure: bool = False
    # 로그인 brute-force 대응: 이 기간(초) 동안 이 횟수만큼 실패하면 추가 시도를 차단한다.
    admin_login_max_attempts: int = 5
    admin_login_lockout_seconds: int = 300

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()
