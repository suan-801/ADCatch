import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Ad, AdObservation, AdStatusEvent, CollectionRun, Competitor, Project, User
from app.schemas import ProjectCreate, ProjectOut, ProjectSummaryOut, ProjectUpdate
from app.services import storage

router = APIRouter(prefix="/projects", tags=["projects"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ProjectOut)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _admin: bool = Depends(require_admin),
):
    project = Project(user_id=user.id, name=payload.name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.scalars(select(Project).where(Project.user_id == user.id)).all()


@router.get("/summary", response_model=list[ProjectSummaryOut])
def list_projects_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """§13-2 성능 최적화 — 랜딩 페이지의 listProjects()+N×(listCompetitors+getDashboard) 조합을
    이 엔드포인트 1회 호출로 대체한다. 값의 의미는 기존 조합과 동일하다(브랜드 수 / 활성 광고 수).
    경로 등록 순서 주의: "/summary"는 "/{project_id}"보다 먼저 등록해야 project_id로 오해되지 않는다."""
    projects = db.scalars(select(Project).where(Project.user_id == user.id)).all()
    if not projects:
        return []
    project_ids = [p.id for p in projects]

    competitor_counts = dict(
        db.execute(
            select(Competitor.project_id, func.count())
            .where(Competitor.project_id.in_(project_ids))
            .group_by(Competitor.project_id)
        ).all()
    )
    active_ad_counts = dict(
        db.execute(
            select(Competitor.project_id, func.count())
            .join(Ad, Ad.competitor_id == Competitor.id)
            .where(
                Competitor.project_id.in_(project_ids),
                Ad.status == "ACTIVE",
                Ad.is_archived.is_(False),
            )
            .group_by(Competitor.project_id)
        ).all()
    )

    return [
        ProjectSummaryOut(
            id=p.id,
            name=p.name,
            status=p.status,
            auto_collect_enabled=p.auto_collect_enabled,
            created_at=p.created_at,
            competitor_count=competitor_counts.get(p.id, 0),
            active_ad_count=active_ad_counts.get(p.id, 0),
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _admin: bool = Depends(require_admin),
):
    """Baseline Opt-in CTA / Project Header 설정에서 auto_collect_enabled를 토글한다."""
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.auto_collect_enabled is not None:
        project.auto_collect_enabled = payload.auto_collect_enabled

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _admin: bool = Depends(require_admin),
):
    """Part H: Project + 소속 Brand/Ad/수집 이력을 함께 삭제한다. 다른 Project의 데이터는
    절대 건드리지 않는다 — 전부 이 project_id 소속 competitor_id로 한정해서 지운다.

    Competitor→Ad는 기존 ORM relationship(cascade="all, delete-orphan")을 그대로 재사용하되,
    CollectionRun/AdObservation/AdStatusEvent는 Competitor에 매핑된 relationship이 없으므로
    (DB의 ON DELETE CASCADE FK는 Postgres에서는 동작하지만 SQLite 등에서는 보장되지 않는다)
    명시적으로 먼저 지워 어떤 DB 백엔드에서도 동일하게 동작하도록 한다."""
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    competitor_ids = [c.id for c in project.competitors]

    if competitor_ids:
        db.query(AdStatusEvent).filter(AdStatusEvent.competitor_id.in_(competitor_ids)).delete(
            synchronize_session=False
        )
        db.query(AdObservation).filter(AdObservation.competitor_id.in_(competitor_ids)).delete(
            synchronize_session=False
        )
        db.query(CollectionRun).filter(CollectionRun.competitor_id.in_(competitor_ids)).delete(
            synchronize_session=False
        )

    db.delete(project)  # ORM cascade: Project -> Competitor -> Ad
    db.commit()

    # H-03: Storage 정리는 best-effort — 실패해도 위 DB 삭제(이미 commit됨)를 되돌리지 않는다.
    for competitor_id in competitor_ids:
        if not storage.cleanup_prefix(f"{competitor_id}/"):
            logger.warning(
                "project delete: storage cleanup failed for competitor_id=%s (orphaned thumbnails may remain)",
                competitor_id,
            )
