from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.routers import ad_changes, ads, competitors, dashboard, projects

app = FastAPI(title="ADCatcher API", version="0.1.0")

# P0-11: 허용 origin을 환경변수(CORS_ALLOWED_ORIGINS, 콤마 구분)로 설정 — 로컬 기본값은
# 기존과 동일하게 http://localhost:3000 하나만 유지된다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Starlette의 기본 미처리 예외 처리는 CORSMiddleware 바깥에서 500을 생성해
    # 응답에 CORS 헤더가 붙지 않는다 — 브라우저는 이를 실제 오류 메시지 대신
    # "Failed to fetch"로 표시한다. 커스텀 핸들러는 CORSMiddleware 안쪽에서 실행되므로
    # 이 문제를 피한다.
    return JSONResponse(status_code=500, content={"detail": f"Internal server error: {exc}"})

app.include_router(projects.router)
app.include_router(competitors.router)
app.include_router(ads.router)
app.include_router(dashboard.router)
app.include_router(ad_changes.router)


@app.on_event("startup")
def on_startup() -> None:
    # MVP: Alembic 마이그레이션 대신 시작 시 테이블을 보장한다.
    # 운영 전환 시 apps/api/db/schema.sql 을 Supabase SQL Editor에서 직접 실행하는 편을 권장.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
