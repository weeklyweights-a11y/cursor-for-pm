"""Orchestrate brief section generation and load theme context (Phase 7)."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.brief import Brief
from app.models.customer import Customer
from app.models.feedback_item import FeedbackItem
from app.models.product_context import ProductContext
from app.models.scoring_config import ScoringConfig
from app.models.theme import Theme
from app.services import brief_section_generators
from app.utils.logging import get_logger

logger = get_logger(__name__)

SECTION_ORDER = [
    "problem_statement",
    "customer_impact",
    "evidence_summary",
    "trend_analysis",
    "business_case",
    "recommended_action",
    "risks",
]


def _theme_to_dict(t: Theme) -> dict:
    return {
        "id": str(t.id),
        "name": t.name,
        "description": t.description or "",
        "mention_count": t.mention_count,
        "unique_customers": t.unique_customers,
        "segment_breakdown": t.segment_breakdown,
        "urgency_breakdown": t.urgency_breakdown,
        "sentiment_breakdown": t.sentiment_breakdown,
        "priority_score": t.priority_score,
        "score_breakdown": t.score_breakdown,
    }


def _feedback_to_dict(f: FeedbackItem) -> dict:
    return {
        "id": str(f.id),
        "content": f.content or "",
        "pain_point": f.pain_point,
        "topic": f.topic,
        "feature_gap": f.feature_gap,
        "urgency": f.urgency,
        "verbatim_quote": f.verbatim_quote,
        "created_at": f.created_at.isoformat() if f.created_at else None,
        "customer_name": f.customer_name,
        "segment": f.segment,
    }


def _customer_to_dict(c: Customer) -> dict:
    return {
        "id": str(c.id),
        "domain": c.domain,
        "company_name": c.company_name,
        "segment": c.segment,
    }


def load_theme_context(db: Session, org_id: UUID, theme_id: UUID) -> dict:
    """Load theme, feedback items, customers, scoring config, product context as dicts."""
    theme = db.query(Theme).filter(Theme.id == theme_id, Theme.org_id == org_id).first()
    if not theme:
        return {}
    items = db.query(FeedbackItem).filter(
        FeedbackItem.theme_id == theme_id,
        FeedbackItem.org_id == org_id,
    ).all()
    theme_data = _theme_to_dict(theme)
    feedback_items = [_feedback_to_dict(i) for i in items]
    customer_ids = {i.customer_id for i in items if i.customer_id}
    customers = []
    if customer_ids:
        customers = db.query(Customer).filter(Customer.id.in_(customer_ids), Customer.org_id == org_id).all()
    customers = [_customer_to_dict(c) for c in customers]
    scoring = db.query(ScoringConfig).filter(ScoringConfig.org_id == org_id).first()
    scoring_config = {"goals": scoring.goals} if scoring else None
    product = db.query(ProductContext).filter(ProductContext.org_id == org_id).first()
    product_context = (
        {
            "product_name": product.product_name,
            "product_description": product.product_description,
            "known_limitations": product.known_limitations,
            "target_users": product.target_users,
        }
        if product
        else None
    )
    all_themes = db.query(Theme).filter(Theme.org_id == org_id, Theme.is_current == True).limit(20).all()
    return {
        "theme_data": theme_data,
        "feedback_items": feedback_items,
        "customers": customers,
        "scoring_config": scoring_config,
        "product_context": product_context,
        "all_themes": [_theme_to_dict(t) for t in all_themes],
    }


def _make_section(key: str, content: str) -> dict:
    title = brief_section_generators.SECTION_TITLES.get(key, key.replace("_", " ").title())
    now = datetime.now(timezone.utc).isoformat()
    return {
        "key": key,
        "title": title,
        "content": content,
        "generated_at": now,
        "edited": False,
        "edit_history": [],
    }


def generate_all_sections(db: Session, org_id: UUID, brief_id: UUID, theme_id: UUID) -> None:
    """Generate all 7 sections sequentially; update brief after each. Retry once on section failure."""
    from app.exceptions import ExternalServiceError

    ctx = load_theme_context(db, org_id, theme_id)
    if not ctx:
        brief = db.query(Brief).filter(Brief.id == brief_id, Brief.org_id == org_id).first()
        if brief:
            brief.status = "failed"
            db.commit()
        return
    theme_data = ctx["theme_data"]
    feedback_items = ctx["feedback_items"]
    customers = ctx["customers"]
    scoring_config = ctx["scoring_config"]
    product_context = ctx["product_context"]
    all_themes = ctx["all_themes"]

    brief = db.query(Brief).filter(Brief.id == brief_id, Brief.org_id == org_id).first()
    if not brief:
        return
    sections = list(brief.sections or [])

    for key in SECTION_ORDER:
        content = brief_section_generators.FAILED_PLACEHOLDER
        for attempt in range(2):
            try:
                if key == "problem_statement":
                    content = brief_section_generators.generate_problem_statement(theme_data, feedback_items)
                elif key == "customer_impact":
                    content = brief_section_generators.generate_customer_impact(theme_data, customers)
                elif key == "evidence_summary":
                    content = brief_section_generators.generate_evidence_summary(theme_data, feedback_items)
                elif key == "trend_analysis":
                    content = brief_section_generators.generate_trend_analysis(theme_data, feedback_items)
                elif key == "business_case":
                    content = brief_section_generators.generate_business_case(
                        theme_data, scoring_config, product_context
                    )
                elif key == "recommended_action":
                    content = brief_section_generators.generate_recommended_action(
                        theme_data, feedback_items, product_context
                    )
                elif key == "risks":
                    content = brief_section_generators.generate_risks(theme_data, feedback_items, all_themes)
                break
            except (ExternalServiceError, Exception) as e:
                logger.warning("Brief section %s attempt %s failed: %s", key, attempt + 1, str(e))
                if attempt == 1:
                    content = brief_section_generators.FAILED_PLACEHOLDER

        existing = next((s for s in sections if s.get("key") == key), None)
        if existing:
            existing["content"] = content
            existing["generated_at"] = datetime.now(timezone.utc).isoformat()
        else:
            sections.append(_make_section(key, content))
        brief.sections = sections
        db.commit()
        db.refresh(brief)

    brief.status = "completed"
    db.commit()
