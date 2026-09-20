import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import AdObservation, AdStatusEvent, CollectionRun, Project, User
from app.schemas import ProjectCreate, ProjectOut, ProjectUpdate
from app.services import storage

router = APIRouter(prefix="/projects", tags=["projects"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ProjectOut)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
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
