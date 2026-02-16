"""Spec CRUD and orchestration (Phase 8). All queries filter by org_id."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.brief import Brief
from app.models.spec import Spec
from app.services import spec_generation_service
from app.services import spec_section_generators
from app.utils.logging import get_logger

logger = get_logger(__name__)

SECTION_ORDER = spec_generation_service.SECTION_ORDER
MAX_EDIT_HISTORY = 3


def generate_spec(
    db: Session,
    org_id: UUID,
    brief_id: UUID,
    user_id: UUID,
    scope: str,
    target_audience: str,
    custom_instructions: str | None = None,
) -> UUID | None:
    """Create spec record, validate brief has solution_evaluation, queue task, return spec id."""
    brief = db.query(Brief).filter(Brief.id == brief_id, Brief.org_id == org_id).first()
    if not brief:
        return None
    if not (brief.solution_evaluation and isinstance(brief.solution_evaluation, dict)):
        return None
    prev = (
        db.query(Spec)
        .filter(Spec.org_id == org_id, Spec.brief_id == brief_id)
        .order_by(Spec.version.desc())
        .first()
    )
    version = (prev.version + 1) if prev else 1
    if prev:
        prev.is_current = False
    theme_name = getattr(brief.theme, "name", "Theme") if brief.theme else "Theme"
    title = f"{theme_name} — Implementation Spec"
    spec = Spec(
        org_id=org_id,
        brief_id=brief_id,
        theme_id=brief.theme_id,
        created_by=user_id,
        version=version,
        status="generating",
        title=title,
        scope=scope,
        target_audience=target_audience,
        sections=[],
        config={
            "scope": scope,
            "target_audience": target_audience,
            "custom_instructions": custom_instructions or "",
        },
        is_current=True,
    )
    db.add(spec)
    db.commit()
    db.refresh(spec)
    from app.tasks.spec_tasks import generate_spec_task

    generate_spec_task.delay(
        str(spec.id), str(org_id), str(brief_id), spec.config or {}
    )
    return spec.id


def get_spec(db: Session, org_id: UUID, spec_id: UUID) -> Spec | None:
    return db.query(Spec).filter(Spec.id == spec_id, Spec.org_id == org_id).first()


def get_specs_for_brief(db: Session, org_id: UUID, brief_id: UUID) -> list[Spec]:
    return (
        db.query(Spec)
        .filter(Spec.org_id == org_id, Spec.brief_id == brief_id)
        .order_by(Spec.version.desc())
        .all()
    )


def get_current_spec(db: Session, org_id: UUID, brief_id: UUID) -> Spec | None:
    return (
        db.query(Spec)
        .filter(
            Spec.org_id == org_id,
            Spec.brief_id == brief_id,
            Spec.is_current == True,
        )
        .first()
    )


def get_specs_for_theme(db: Session, org_id: UUID, theme_id: UUID) -> list[Spec]:
    return (
        db.query(Spec)
        .filter(Spec.org_id == org_id, Spec.theme_id == theme_id)
        .order_by(Spec.version.desc())
        .all()
    )


def _find_section(sections: list, section_key: str) -> dict | None:
    for s in sections or []:
        if s.get("key") == section_key:
            return s
    return None


def regenerate_section(
    db: Session, org_id: UUID, spec_id: UUID, section_key: str
) -> bool:
    """Append current content to edit_history (cap 3), regenerate, replace content."""
    spec = get_spec(db, org_id, spec_id)
    if not spec or section_key not in SECTION_ORDER:
        return False
    sections = list(spec.sections or [])
    sec = _find_section(sections, section_key)
    if not sec:
        return False
    history = list(sec.get("edit_history") or [])
    history.append(
        {"content": sec.get("content"), "at": datetime.now(timezone.utc).isoformat()}
    )
    sec["edit_history"] = history[-MAX_EDIT_HISTORY:]
    ctx = spec_generation_service.load_generation_context(db, org_id, spec.brief_id)
    if not ctx:
        return False
    brief_data = ctx["brief_data"]
    theme_data = ctx["theme_data"]
    product_context = ctx["product_context"]
    raw_eval = brief_data.get("solution_evaluation") or {}
    solution_eval = raw_eval.get("evaluation") or raw_eval
    config = dict(spec.config or {})
    config["product_context"] = product_context
    config["solution_description"] = (
        raw_eval.get("solution_description")
        or solution_eval.get("solution_description")
        or ""
    )[:5000]
    try:
        if section_key == "executive_summary":
            content = spec_section_generators.generate_executive_summary(
                brief_data, solution_eval, config
            )
        elif section_key == "background_evidence":
            content = spec_section_generators.generate_background_evidence(
                brief_data, theme_data, config
            )
        elif section_key == "user_stories":
            content = spec_section_generators.generate_user_stories(
                solution_eval, theme_data, config
            )
        elif section_key == "functional_requirements":
            us_content = _section_content(sections, "user_stories")
            content = spec_section_generators.generate_functional_requirements(
                us_content, brief_data, config
            )
        elif section_key == "technical_guidance":
            fr_content = _section_content(sections, "functional_requirements")
            content = spec_section_generators.generate_technical_guidance(
                fr_content, product_context, config
            )
        elif section_key == "data_model_changes":
            fr_content = _section_content(sections, "functional_requirements")
            content = spec_section_generators.generate_data_model(
                fr_content, product_context, config
            )
        elif section_key == "api_contracts":
            fr_content = _section_content(sections, "functional_requirements")
            us_content = _section_content(sections, "user_stories")
            dm_content = _section_content(sections, "data_model_changes")
            content = spec_section_generators.generate_api_contracts(
                fr_content, us_content, dm_content, config
            )
        elif section_key == "testing_verification":
            us_content = _section_content(sections, "user_stories")
            fr_content = _section_content(sections, "functional_requirements")
            content = spec_section_generators.generate_testing_verification(
                us_content, fr_content, solution_eval, config
            )
        else:
            return False
    except Exception as e:
        logger.warning("Regenerate spec section %s failed: %s", section_key, e)
        return False
    sec["content"] = content
    sec["edited"] = False
    sec["generated_at"] = datetime.now(timezone.utc).isoformat()
    spec.sections = sections
    db.commit()
    return True


def _section_content(sections: list, key: str) -> str:
    for s in sections or []:
        if s.get("key") == key:
            return s.get("content") or ""
    return ""


def edit_section(
    db: Session, org_id: UUID, spec_id: UUID, section_key: str, new_content: str
) -> bool:
    """Append current to edit_history, set content, edited=true."""
    spec = get_spec(db, org_id, spec_id)
    if not spec:
        return False
    sec = _find_section(spec.sections or [], section_key)
    if not sec:
        return False
    history = list(sec.get("edit_history") or [])
    history.append(
        {"content": sec.get("content"), "at": datetime.now(timezone.utc).isoformat()}
    )
    sec["edit_history"] = history[-MAX_EDIT_HISTORY:]
    sec["content"] = new_content
    sec["edited"] = True
    db.commit()
    return True


def export_spec_markdown(db: Session, org_id: UUID, spec_id: UUID) -> tuple[str, str] | None:
    """Return (markdown_string, filename) or None. Clean output, no debug/metadata."""
    spec = get_spec(db, org_id, spec_id)
    if not spec:
        return None
    parts = [f"# {spec.title}\n", f"*Version {spec.version} | {spec.scope} | {spec.target_audience}*\n"]
    for s in (spec.sections or []):
        parts.append(f"## {s.get('title', s.get('key', ''))}\n\n")
        parts.append((s.get("content") or "") + "\n\n")
    filename = f"{spec.title[:50].replace(' ', '_')}_v{spec.version}.md"
    return "\n".join(parts).strip(), filename


def _section_content_by_key(sections: list, key: str) -> str:
    for s in sections or []:
        if s.get("key") == key:
            return s.get("content") or ""
    return ""


def export_spec_cursor_format(db: Session, org_id: UUID, spec_id: UUID) -> tuple[str, str] | None:
    """Return (cursor-optimized markdown, filename) or None."""
    spec = get_spec(db, org_id, spec_id)
    if not spec:
        return None
    sections = spec.sections or []
    from app.prompts.spec_prompts_loader import get_cursor_export_template

    template = get_cursor_export_template()
    if not template:
        return export_spec_markdown(db, org_id, spec_id)
    goal = _section_content_by_key(sections, "executive_summary")
    done_means = _section_content_by_key(sections, "background_evidence")
    evidence_summary = _section_content_by_key(sections, "background_evidence")
    data_model_changes = _section_content_by_key(sections, "data_model_changes")
    api_contracts = _section_content_by_key(sections, "api_contracts")
    acceptance_criteria = _section_content_by_key(sections, "user_stories")
    non_negotiables = _section_content_by_key(sections, "functional_requirements")
    evidence_trail = _section_content_by_key(sections, "background_evidence")
    content = template.format(
        title=spec.title,
        goal=goal,
        done_means=done_means,
        evidence_summary=evidence_summary,
        data_model_changes=data_model_changes,
        api_contracts=api_contracts,
        acceptance_criteria=acceptance_criteria,
        non_negotiables=non_negotiables,
        evidence_trail=evidence_trail,
    )
    filename = f"{spec.title[:50].replace(' ', '_')}_cursor_v{spec.version}.md"
    return content.strip(), filename


def get_spec_generation_status(db: Session, org_id: UUID, spec_id: UUID) -> dict | None:
    """Return status, sections_completed, sections_total, current_section."""
    spec = get_spec(db, org_id, spec_id)
    if not spec:
        return None
    sections = spec.sections or []
    completed = len(
        [
            s
            for s in sections
            if s.get("content")
            and s.get("content") != spec_section_generators.FAILED_PLACEHOLDER
        ]
    )
    total = len(SECTION_ORDER)
    current = SECTION_ORDER[len(sections)] if len(sections) < total else None
    return {
        "spec_id": str(spec_id),
        "status": spec.status,
        "sections_completed": completed,
        "sections_total": total,
        "current_section": current,
    }
