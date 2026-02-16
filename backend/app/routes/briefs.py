"""Brief API (Phase 7)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user_dependency
from app.models.user import User
from app.schemas.brief import (
    EditSectionRequest,
    EvaluateSolutionRequest,
    GenerateBriefRequest,
)
from app.services import brief_service

router = APIRouter(prefix="/briefs", tags=["briefs"])


def _brief_to_response(brief):
    """Map Brief ORM to BriefResponse-like dict with sections as list of dicts."""
    sections = []
    for s in (brief.sections or []):
        sections.append({
            "key": s.get("key"),
            "title": s.get("title"),
            "content": s.get("content"),
            "generated_at": s.get("generated_at"),
            "edited": s.get("edited", False),
            "edit_history": s.get("edit_history", []),
        })
    return {
        "id": brief.id,
        "theme_id": brief.theme_id,
        "version": brief.version,
        "status": brief.status,
        "title": brief.title,
        "sections": sections,
        "solution_evaluation": brief.solution_evaluation,
        "metadata": getattr(brief, "metadata_", None),
        "is_current": brief.is_current,
        "created_at": brief.created_at,
        "updated_at": brief.updated_at,
    }


@router.post("/generate")
def generate_brief(
    body: GenerateBriefRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Start brief generation for a theme. Returns brief_id and status."""
    brief_id = brief_service.generate_brief(
        db, current_user.org_id, body.theme_id, current_user.id
    )
    if not brief_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Theme not found.")
    return {"data": {"brief_id": str(brief_id), "status": "generating"}}


@router.get("/theme/{theme_id}")
def list_briefs_for_theme(
    theme_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """List all brief versions for a theme."""
    briefs = brief_service.get_briefs_for_theme(db, current_user.org_id, theme_id)
    return {"data": [_brief_to_response(b) for b in briefs]}


@router.get("/theme/{theme_id}/current")
def get_current_brief_for_theme(
    theme_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Get the current (latest) brief for a theme."""
    brief = brief_service.get_current_brief(db, current_user.org_id, theme_id)
    if not brief:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No brief found for this theme.")
    return {"data": _brief_to_response(brief)}


@router.get("/{brief_id}")
def get_brief(
    brief_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Get brief with all sections."""
    brief = brief_service.get_brief(db, current_user.org_id, brief_id)
    if not brief:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found.")
    return {"data": _brief_to_response(brief)}


@router.get("/{brief_id}/status")
def get_brief_status(
    brief_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Get generation progress."""
    status_data = brief_service.get_brief_generation_status(db, current_user.org_id, brief_id)
    if not status_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found.")
    return {"data": status_data}


@router.patch("/{brief_id}/sections/{section_key}")
def edit_section(
    brief_id: UUID,
    section_key: str,
    body: EditSectionRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Edit a section's content."""
    ok = brief_service.edit_section(db, current_user.org_id, brief_id, section_key, body.content)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief or section not found.")
    brief = brief_service.get_brief(db, current_user.org_id, brief_id)
    return {"data": _brief_to_response(brief)}


@router.post("/{brief_id}/sections/{section_key}/regenerate")
def regenerate_section(
    brief_id: UUID,
    section_key: str,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Regenerate a single section."""
    ok = brief_service.regenerate_section(db, current_user.org_id, brief_id, section_key)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief or section not found.")
    brief = brief_service.get_brief(db, current_user.org_id, brief_id)
    return {"data": _brief_to_response(brief)}


@router.post("/{brief_id}/evaluate-solution")
def evaluate_solution(
    brief_id: UUID,
    body: EvaluateSolutionRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Submit solution for evaluation."""
    ok = brief_service.evaluate_solution(
        db, current_user.org_id, brief_id, body.solution_description
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found or invalid request.")
    brief = brief_service.get_brief(db, current_user.org_id, brief_id)
    return {"data": _brief_to_response(brief)}


@router.get("/{brief_id}/export/markdown")
def export_brief_markdown(
    brief_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Export brief as markdown."""
    result = brief_service.export_brief_markdown(db, current_user.org_id, brief_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found.")
    content, filename = result
    return {"data": {"markdown_content": content, "filename": filename}}
