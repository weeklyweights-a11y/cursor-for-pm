"""Orchestrate spec section generation and load context (Phase 8)."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.brief import Brief
from app.models.customer import Customer
from app.models.feedback_item import FeedbackItem
from app.models.product_context import ProductContext
from app.models.scoring_config import ScoringConfig
from app.models.spec import Spec
from app.models.theme import Theme
from app.services import spec_section_generators
from app.utils.logging import get_logger

logger = get_logger(__name__)

SECTION_ORDER = [
    "executive_summary",
    "background_evidence",
    "user_stories",
    "functional_requirements",
    "technical_guidance",
    "data_model_changes",
    "api_contracts",
    "testing_verification",
]


def _theme_to_dict(t: Theme) -> dict:
    return {
        "id": str(t.id),
        "name": t.name,
        "description": t.description or "",
        "mention_count": t.mention_count,
        "score_breakdown": t.score_breakdown,
        "top_quotes": t.top_quotes or [],
    }


def _feedback_to_dict(f: FeedbackItem) -> dict:
    return {
        "id": str(f.id),
        "content": (f.content or "")[:500],
        "pain_point": f.pain_point,
        "verbatim_quote": f.verbatim_quote,
        "customer_name": f.customer_name,
        "segment": f.segment,
    }


def load_generation_context(db: Session, org_id: UUID, brief_id: UUID) -> dict:
    """Load brief (sections + solution_evaluation), theme, feedback, customers, scoring, product context."""
    brief = db.query(Brief).filter(Brief.id == brief_id, Brief.org_id == org_id).first()
    if not brief:
        return {}
    theme = db.query(Theme).filter(Theme.id == brief.theme_id, Theme.org_id == org_id).first()
    if not theme:
        return {}
    items = db.query(FeedbackItem).filter(
        FeedbackItem.theme_id == brief.theme_id,
        FeedbackItem.org_id == org_id,
    ).all()
    product = db.query(ProductContext).filter(ProductContext.org_id == org_id).first()
    product_context = (
        {
            "product_name": product.product_name,
            "product_description": product.product_description,
            "known_limitations": product.known_limitations,
            "target_users": product.target_users,
        }
        if product
        else {}
    )
    brief_data = {
        "theme_name": theme.name,
        "sections": list(brief.sections or []),
        "solution_evaluation": brief.solution_evaluation or {},
    }
    theme_data = {
        **_theme_to_dict(theme),
        "feedback_items": [_feedback_to_dict(i) for i in items],
        "product_context": product_context,
    }
    return {
        "brief_data": brief_data,
        "theme_data": theme_data,
        "product_context": product_context,
    }


def _make_section(key: str, content: str) -> dict:
    title = spec_section_generators.SECTION_TITLES.get(key, key.replace("_", " ").title())
    now = datetime.now(timezone.utc).isoformat()
    return {
        "key": key,
        "title": title,
        "content": content,
        "generated_at": now,
        "edited": False,
        "edit_history": [],
    }


def _section_content(sections: list, key: str) -> str:
    for s in sections or []:
        if s.get("key") == key:
            return s.get("content") or ""
    return ""


def generate_all_sections(
    db: Session, org_id: UUID, spec_id: UUID, brief_id: UUID, config: dict
) -> None:
    """Generate all 8 sections sequentially; update spec after each. Retry once on failure."""
    from app.exceptions import ExternalServiceError

    ctx = load_generation_context(db, org_id, brief_id)
    if not ctx:
        spec = db.query(Spec).filter(Spec.id == spec_id, Spec.org_id == org_id).first()
        if spec:
            spec.status = "failed"
            db.commit()
        return
    brief_data = ctx["brief_data"]
    theme_data = ctx["theme_data"]
    product_context = ctx["product_context"]
    raw_eval = brief_data.get("solution_evaluation") or {}
    solution_eval = raw_eval.get("evaluation") or raw_eval
    config["product_context"] = product_context
    config["solution_description"] = (raw_eval.get("solution_description") or solution_eval.get("solution_description") or "")[:5000]

    spec = db.query(Spec).filter(Spec.id == spec_id, Spec.org_id == org_id).first()
    if not spec:
        return
    sections = list(spec.sections or [])

    user_stories_content = ""
    functional_requirements_content = ""
    data_model_content = ""

    for key in SECTION_ORDER:
        content = spec_section_generators.FAILED_PLACEHOLDER
        for attempt in range(2):
            try:
                if key == "executive_summary":
                    content = spec_section_generators.generate_executive_summary(
                        brief_data, solution_eval, config
                    )
                elif key == "background_evidence":
                    content = spec_section_generators.generate_background_evidence(
                        brief_data, theme_data, config
                    )
                elif key == "user_stories":
                    content = spec_section_generators.generate_user_stories(
                        solution_eval, theme_data, config
                    )
                    user_stories_content = content
                elif key == "functional_requirements":
                    content = spec_section_generators.generate_functional_requirements(
                        user_stories_content, brief_data, config
                    )
                    functional_requirements_content = content
                elif key == "technical_guidance":
                    content = spec_section_generators.generate_technical_guidance(
                        functional_requirements_content, product_context, config
                    )
                elif key == "data_model_changes":
                    content = spec_section_generators.generate_data_model(
                        functional_requirements_content, product_context, config
                    )
                    data_model_content = content
                elif key == "api_contracts":
                    content = spec_section_generators.generate_api_contracts(
                        functional_requirements_content,
                        user_stories_content,
                        data_model_content,
                        config,
                    )
                elif key == "testing_verification":
                    content = spec_section_generators.generate_testing_verification(
                        user_stories_content,
                        functional_requirements_content,
                        solution_eval,
                        config,
                    )
                break
            except (ExternalServiceError, Exception) as e:
                logger.warning("Spec section %s attempt %s failed: %s", key, attempt + 1, str(e))
                if attempt == 1:
                    content = spec_section_generators.FAILED_PLACEHOLDER

        existing = next((s for s in sections if s.get("key") == key), None)
        if existing:
            existing["content"] = content
            existing["generated_at"] = datetime.now(timezone.utc).isoformat()
        else:
            sections.append(_make_section(key, content))
        spec.sections = sections
        db.commit()
        db.refresh(spec)

    spec.status = "completed"
    db.commit()
