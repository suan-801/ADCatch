import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Competitor, Project, User
from app.schemas import CompetitorCreate, CompetitorOut
from app.services.ad_library_collector import extract_page_id

router = APIRouter(prefix="/projects/{project_id}/competitors", tags=["competitors"])


def _get_owned_project(db: Session, project_id: uuid.UUID, user: User) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=CompetitorOut)
def create_competitor(
    project_id: uuid.UUID,
    payload: CompetitorCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, user)
    competitor = Competitor(
        project_id=project_id,
        name=payload.name,
        ad_library_url=payload.ad_library_url,
        page_id=extract_page_id(payload.ad_library_url),
        is_own_brand=payload.is_own_brand,
    )
    db.add(competitor)
    db.commit()
    db.refresh(competitor)
    return competitor


@router.get("", response_model=list[CompetitorOut])
def list_competitors(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, user)
    return db.scalars(select(Competitor).where(Competitor.project_id == project_id)).all()
