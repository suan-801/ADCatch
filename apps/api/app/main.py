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
    # 주의: FastAPI/Starlette에서 bare Exception용 핸들러는 ServerErrorMiddleware(가장 바깥 레이어)에서
    # 실행되며, 이는 CORSMiddleware보다도 바깥쪽이다 — 즉 이 핸들러가 만든 응답에는 CORSMiddleware가
    # 자동으로 CORS 헤더를 붙여주지 않는다(이전 주석의 "CORSMiddleware 안쪽이라 안전하다"는 설명은
    # 틀렸었다 — 실제로 재현해서 확인: 500 응답에 access-control-allow-origin이 빠져 있었음).
    # 브라우저는 CORS 헤더 없는 응답을 읽지 못하게 막아버리므로, 실제 500 상세 메시지 대신
    # fetch() 자체가 "TypeError: Failed to fetch"로 실패한 것처럼 보인다 — 그래서 여기서 직접
    # 헤더를 붙인다.
    response = JSONResponse(status_code=500, content={"detail": f"Internal server error: {exc}"})
    origin = request.headers.get("origin")
    if origin in settings.cors_allowed_origins_list:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response

app.include_router(projects.router)
app.include_router(competitors.router)
app.include_router(ads.router)
app.include_router(dashboard.router)
app.include_router(ad_changes.router)


@app.on_event("startup")
def on_startup() -> None:
    # MVP: Alembic 마이그레이션 대신 시작 시 테이블을 보장한다.
    # 운영 전환 시 apps/api/db/schema.sql 을 Supabase SQL Editor에서 직접 실행하는 편을 권장.
    #
    # P0-13 주의: create_all()은 "존재하지 않는 테이블"만 생성한다 — 이미 존재하는 테이블에
    # 새 column을 추가해주지 않는다. 즉 "서버를 재시작하면 DB가 최신 schema가 된다"는 가정은
    # 틀렸다. 이미 배포된 DB에 새 column(예: ads.source_started_at, competitors.baseline_completed_at)을
    # 반영하려면 apps/api/db/migrations/ 의 additive migration을 직접 실행해야 한다.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
