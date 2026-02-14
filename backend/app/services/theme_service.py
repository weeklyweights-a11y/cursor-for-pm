"""Theme CRUD and naming (Phase 5)."""

from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.feedback_item import FeedbackItem
from app.models.theme import Theme
from app.services.llm_service import call_llm

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load_theme_naming_system() -> str:
    path = _PROMPTS_DIR / "theme_naming_system.txt"
    return path.read_text().strip()


def _load_theme_naming_user_template() -> str:
    path = _PROMPTS_DIR / "theme_naming_user.txt"
    return path.read_text().strip()


def name_theme_from_quotes(quotes: list[str], fallback_name: str = "Theme", fallback_desc: str = "Cluster of related feedback items.") -> tuple[str, str]:
    """Call LLM to name theme from quotes. Returns (name, description)."""
    if not quotes:
        return fallback_name, fallback_desc
    system = _load_theme_naming_system()
    template = _load_theme_naming_user_template()
    quotes_block = "\n".join(f"- {q[:500]}" for q in quotes[:15] if q)
    prompt = template.format(quotes_block=quotes_block)
    try:
        result, _ = call_llm(prompt, system, temperature=0.3, max_tokens=256)
        name = (result.get("name") or fallback_name).strip()[:255]
        desc = (result.get("description") or fallback_desc).strip()
        return name, desc
    except Exception:
        return fallback_name, fallback_desc


def get_themes(db: Session, org_id: UUID, page: int = 1, page_size: int = 20, sort_by: str = "priority_score") -> tuple[list[Theme], int]:
    """Return (themes, total) for org, is_current=True, paginated and sorted."""
    q = db.query(Theme).filter(Theme.org_id == org_id, Theme.is_current == True)
    total = q.count()
    order_col = getattr(Theme, sort_by, Theme.priority_score)
    q = q.order_by(order_col.desc().nullslast())
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_theme(db: Session, org_id: UUID, theme_id: UUID) -> Theme | None:
    """Return theme by id if it belongs to org."""
    return db.query(Theme).filter(Theme.org_id == org_id, Theme.id == theme_id).first()


def get_theme_feedback(db: Session, org_id: UUID, theme_id: UUID, page: int = 1, page_size: int = 20) -> tuple[list[FeedbackItem], int]:
    """Return (items, total) for feedback items in this theme."""
    q = db.query(FeedbackItem).filter(FeedbackItem.org_id == org_id, FeedbackItem.theme_id == theme_id)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_outliers(db: Session, org_id: UUID, page: int = 1, page_size: int = 20) -> tuple[list[FeedbackItem], int]:
    """Return (items, total) for is_outlier=True and clustered_at not null."""
    q = db.query(FeedbackItem).filter(
        FeedbackItem.org_id == org_id,
        FeedbackItem.is_outlier == True,
        FeedbackItem.clustered_at.isnot(None),
    )
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total
