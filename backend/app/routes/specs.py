"""Spec API (Phase 8)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user_dependency
from app.models.user import User
from app.schemas.spec import EditSpecSectionRequest, GenerateSpecRequest
from app.services import spec_service

router = APIRouter(prefix="/specs", tags=["specs"])


def _spec_to_response(spec):
    """Map Spec ORM to response dict."""
    sections = []
    for s in (spec.sections or []):
        sections.append({
            "key": s.get("key"),
            "title": s.get("title"),
            "content": s.get("content"),
            "generated_at": s.get("generated_at"),
            "edited": s.get("edited", False),
            "edit_history": s.get("edit_history", []),
        })
    return {
        "id": spec.id,
        "brief_id": spec.brief_id,
        "theme_id": spec.theme_id,
        "version": spec.version,
        "status": spec.status,
        "title": spec.title,
        "scope": spec.scope,
        "target_audience": spec.target_audience,
        "sections": sections,
        "config": spec.config,
        "metadata": getattr(spec, "metadata_", None),
        "is_current": spec.is_current,
        "created_at": spec.created_at,
        "updated_at": spec.updated_at,
    }


@router.post("/generate")
def generate_spec(
    body: GenerateSpecRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Start spec generation for a brief. Brief must have solution evaluation."""
    spec_id = spec_service.generate_spec(
        db,
        current_user.org_id,
        body.brief_id,
        current_user.id,
        body.scope,
        body.target_audience,
        body.custom_instructions,
    )
    if not spec_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brief not found or has no solution evaluation. Evaluate a solution first.",
        )
    return {"data": {"spec_id": str(spec_id), "status": "generating"}}


@router.get("/brief/{brief_id}")
def list_specs_for_brief(
    brief_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """List all spec versions for a brief."""
    specs = spec_service.get_specs_for_brief(db, current_user.org_id, brief_id)
    return {"data": [_spec_to_response(s) for s in specs]}


@router.get("/brief/{brief_id}/current")
def get_current_spec_for_brief(
    brief_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Get the current (latest) spec for a brief."""
    spec = spec_service.get_current_spec(db, current_user.org_id, brief_id)
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No spec found for this brief.",
        )
    return {"data": _spec_to_response(spec)}


@router.get("/theme/{theme_id}")
def list_specs_for_theme(
    theme_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """List all specs for a theme."""
    specs = spec_service.get_specs_for_theme(db, current_user.org_id, theme_id)
    return {"data": [_spec_to_response(s) for s in specs]}


@router.get("/{spec_id}")
def get_spec(
    spec_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Get spec with all sections."""
    spec = spec_service.get_spec(db, current_user.org_id, spec_id)
    if not spec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spec not found.")
    return {"data": _spec_to_response(spec)}


@router.get("/{spec_id}/status")
def get_spec_status(
    spec_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Get generation progress."""
    status_data = spec_service.get_spec_generation_status(db, current_user.org_id, spec_id)
    if not status_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spec not found.")
    return {"data": status_data}


@router.patch("/{spec_id}/sections/{section_key}")
def edit_section(
    spec_id: UUID,
    section_key: str,
    body: EditSpecSectionRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Edit a section's content."""
    ok = spec_service.edit_section(
        db, current_user.org_id, spec_id, section_key, body.content
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spec or section not found.",
        )
    spec = spec_service.get_spec(db, current_user.org_id, spec_id)
    return {"data": _spec_to_response(spec)}


@router.post("/{spec_id}/sections/{section_key}/regenerate")
def regenerate_section(
    spec_id: UUID,
    section_key: str,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Regenerate a single section."""
    ok = spec_service.regenerate_section(db, current_user.org_id, spec_id, section_key)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spec or section not found.",
        )
    spec = spec_service.get_spec(db, current_user.org_id, spec_id)
    return {"data": _spec_to_response(spec)}


@router.get("/{spec_id}/export/markdown")
def export_spec_markdown(
    spec_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Export spec as standard markdown."""
    result = spec_service.export_spec_markdown(db, current_user.org_id, spec_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spec not found.")
    content, filename = result
    return {
        "data": {
            "markdown_content": content,
            "filename": filename,
            "format": "standard",
        }
    }


@router.get("/{spec_id}/export/cursor")
def export_spec_cursor(
    spec_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Export spec as Cursor-optimized markdown."""
    result = spec_service.export_spec_cursor_format(db, current_user.org_id, spec_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spec not found.")
    content, filename = result
    return {
        "data": {
            "markdown_content": content,
            "filename": filename,
            "format": "cursor",
        }
    }
