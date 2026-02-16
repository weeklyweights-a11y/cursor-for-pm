"""Brief CRUD and orchestration (Phase 7). All queries filter by org_id."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.brief import Brief
from app.models.theme import Theme
from app.services import brief_generation_service
from app.services import brief_section_generators
from app.utils.logging import get_logger

logger = get_logger(__name__)

SECTION_ORDER = brief_generation_service.SECTION_ORDER
MAX_EDIT_HISTORY = 3


def generate_brief(db: Session, org_id: UUID, theme_id: UUID, user_id: UUID) -> UUID | None:
    """Create brief record (status=generating), queue task, return brief id."""
    theme = db.query(Theme).filter(Theme.id == theme_id, Theme.org_id == org_id).first()
    if not theme:
        return None
    prev = db.query(Brief).filter(Brief.org_id == org_id, Brief.theme_id == theme_id).order_by(Brief.version.desc()).first()
    version = (prev.version + 1) if prev else 1
    if prev:
        prev.is_current = False
    title = f"{theme.name} — Evidence Brief"
    brief = Brief(
        org_id=org_id,
        theme_id=theme_id,
        created_by=user_id,
        version=version,
        status="generating",
        title=title,
        sections=[],
        is_current=True,
    )
    db.add(brief)
    db.commit()
    db.refresh(brief)
    from app.tasks.brief_tasks import generate_brief_task
    generate_brief_task.delay(str(brief.id), str(org_id), str(theme_id))
    return brief.id


def get_brief(db: Session, org_id: UUID, brief_id: UUID) -> Brief | None:
    return db.query(Brief).filter(Brief.id == brief_id, Brief.org_id == org_id).first()


def get_briefs_for_theme(db: Session, org_id: UUID, theme_id: UUID) -> list[Brief]:
    return db.query(Brief).filter(Brief.org_id == org_id, Brief.theme_id == theme_id).order_by(Brief.version.desc()).all()


def get_current_brief(db: Session, org_id: UUID, theme_id: UUID) -> Brief | None:
    return db.query(Brief).filter(
        Brief.org_id == org_id,
        Brief.theme_id == theme_id,
        Brief.is_current == True,
    ).first()


def _find_section(sections: list, section_key: str) -> dict | None:
    for s in sections or []:
        if s.get("key") == section_key:
            return s
    return None


def regenerate_section(db: Session, org_id: UUID, brief_id: UUID, section_key: str) -> bool:
    """Append current content to edit_history (cap 3), regenerate, replace content."""
    brief = get_brief(db, org_id, brief_id)
    if not brief or section_key not in SECTION_ORDER:
        return False
    sections = list(brief.sections or [])
    sec = _find_section(sections, section_key)
    if not sec:
        return False
    history = list(sec.get("edit_history") or [])
    history.append({"content": sec.get("content"), "at": datetime.now(timezone.utc).isoformat()})
    sec["edit_history"] = history[-MAX_EDIT_HISTORY:]
    ctx = brief_generation_service.load_theme_context(db, org_id, brief.theme_id)
    if not ctx:
        return False
    try:
        if section_key == "problem_statement":
            content = brief_section_generators.generate_problem_statement(ctx["theme_data"], ctx["feedback_items"])
        elif section_key == "customer_impact":
            content = brief_section_generators.generate_customer_impact(ctx["theme_data"], ctx["customers"])
        elif section_key == "evidence_summary":
            content = brief_section_generators.generate_evidence_summary(ctx["theme_data"], ctx["feedback_items"])
        elif section_key == "trend_analysis":
            content = brief_section_generators.generate_trend_analysis(ctx["theme_data"], ctx["feedback_items"])
        elif section_key == "business_case":
            content = brief_section_generators.generate_business_case(
                ctx["theme_data"], ctx["scoring_config"], ctx["product_context"]
            )
        elif section_key == "recommended_action":
            content = brief_section_generators.generate_recommended_action(
                ctx["theme_data"], ctx["feedback_items"], ctx["product_context"]
            )
        elif section_key == "risks":
            content = brief_section_generators.generate_risks(
                ctx["theme_data"], ctx["feedback_items"], ctx["all_themes"]
            )
        else:
            return False
    except Exception as e:
        logger.warning("Regenerate section %s failed: %s", section_key, e)
        return False
    sec["content"] = content
    sec["edited"] = False
    sec["generated_at"] = datetime.now(timezone.utc).isoformat()
    brief.sections = sections
    db.commit()
    return True


def edit_section(db: Session, org_id: UUID, brief_id: UUID, section_key: str, new_content: str) -> bool:
    """Append current to edit_history, set content, edited=true."""
    brief = get_brief(db, org_id, brief_id)
    if not brief:
        return False
    sec = _find_section(brief.sections or [], section_key)
    if not sec:
        return False
    history = list(sec.get("edit_history") or [])
    history.append({"content": sec.get("content"), "at": datetime.now(timezone.utc).isoformat()})
    sec["edit_history"] = history[-MAX_EDIT_HISTORY:]
    sec["content"] = new_content
    sec["edited"] = True
    db.commit()
    return True


def evaluate_solution(db: Session, org_id: UUID, brief_id: UUID, solution_description: str) -> bool:
    """Run solution evaluation and store in brief.solution_evaluation."""
    brief = get_brief(db, org_id, brief_id)
    if not brief or not solution_description.strip():
        return False
    ctx = brief_generation_service.load_theme_context(db, org_id, brief.theme_id)
    if not ctx:
        return False
    try:
        evaluation = brief_section_generators.evaluate_solution_against_evidence(
            ctx["theme_data"], ctx["feedback_items"], solution_description.strip()
        )
    except Exception as e:
        logger.warning("Solution evaluation failed: %s", e)
        return False
    brief.solution_evaluation = {
        "solution_description": solution_description.strip(),
        "evaluation": evaluation,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
    db.commit()
    return True


def export_brief_markdown(db: Session, org_id: UUID, brief_id: UUID) -> tuple[str, str] | None:
    """Return (markdown_string, filename) or None."""
    brief = get_brief(db, org_id, brief_id)
    if not brief:
        return None
    parts = [f"# {brief.title}\n", f"*Version {brief.version}*\n"]
    for s in (brief.sections or []):
        parts.append(f"## {s.get('title', s.get('key', ''))}\n\n")
        parts.append((s.get("content") or "") + "\n\n")
    filename = f"{brief.title[:50].replace(' ', '_')}_v{brief.version}.md"
    return "\n".join(parts).strip(), filename


def get_brief_generation_status(db: Session, org_id: UUID, brief_id: UUID) -> dict | None:
    """Return status, sections_completed, sections_total, current_section."""
    brief = get_brief(db, org_id, brief_id)
    if not brief:
        return None
    sections = brief.sections or []
    completed = len([s for s in sections if s.get("content") and s.get("content") != brief_section_generators.FAILED_PLACEHOLDER])
    total = len(SECTION_ORDER)
    current = SECTION_ORDER[len(sections)] if len(sections) < total else None
    return {
        "brief_id": str(brief_id),
        "status": brief.status,
        "sections_completed": completed,
        "sections_total": total,
        "current_section": current,
    }
