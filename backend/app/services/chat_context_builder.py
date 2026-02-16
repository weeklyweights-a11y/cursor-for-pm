"""RAG context and prompt building for chat (Phase 6)."""

from pathlib import Path
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.feedback_item import FeedbackItem
from app.models.theme import Theme
from app.services import embedding_service
from app.services.product_context_service import has_product_context, get_product_context
from app.services.rag_service import (
    retrieve_relevant_feedback,
    format_feedback_context,
    format_theme_context,
    format_stats_context,
    estimate_token_count,
    truncate_context,
)
from app.services.theme_service import get_theme

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
TOKEN_BUDGET = 12000
RESPONSE_BUDGET = 4000


def _load_system_prompt() -> str:
    return (_PROMPTS_DIR / "chat_system.txt").read_text().strip()


def _load_user_template() -> str:
    return (_PROMPTS_DIR / "chat_user.txt").read_text().strip()


def build_rag_context(
    db: Session,
    org_id: UUID,
    query_embedding: list[float],
    query_text: str,
    page_context: dict | None = None,
) -> str:
    """Retrieve relevant feedback, enrich with theme/customer, format. If page_context, load that entity first."""
    limit = getattr(settings, "chat_max_rag_items", 20)
    parts = []
    if page_context:
        ptype, pid = page_context.get("type"), page_context.get("id")
        if ptype == "theme" and pid:
            try:
                theme = get_theme(db, org_id, UUID(pid))
                if theme:
                    parts.append(f"[Page context - current theme]\n{theme.name}: {theme.description or ''}. mention_count={theme.mention_count}, priority_score={theme.priority_score}.")
            except ValueError:
                pass
        elif ptype == "feedback" and pid:
            try:
                item = db.query(FeedbackItem).filter(FeedbackItem.org_id == org_id, FeedbackItem.id == UUID(pid)).first()
                if item:
                    parts.append(f"[Page context - feedback]\n{item.content[:300]}...")
            except ValueError:
                pass
        elif ptype == "customer" and pid:
            from app.services.customer_service import get_customer
            try:
                c = get_customer(db, org_id, UUID(pid))
                if c:
                    parts.append(f"[Page context - customer]\n{c.company_name or c.domain}, segment={c.segment}.")
            except ValueError:
                pass
    items = retrieve_relevant_feedback(db, org_id, query_embedding, limit=limit)
    theme_ids = [i.theme_id for i in items if i.theme_id]
    theme_id_to_name = {}
    if theme_ids:
        themes = db.query(Theme).filter(Theme.id.in_(theme_ids), Theme.org_id == org_id).all()
        theme_id_to_name = {t.id: t.name for t in themes}
    parts.append("--- Relevant feedback ---\n" + format_feedback_context(items, theme_id_to_name))
    parts.append("\n--- Top themes ---\n" + format_theme_context(db, org_id, limit=5))
    parts.append("\n--- Stats ---\n" + format_stats_context(db, org_id))
    return "\n".join(parts)


def build_chat_prompt(
    system_prompt: str,
    history: list[dict],
    rag_context: str,
    user_message: str,
) -> list[dict]:
    """Assemble messages: system already applied; then history, then RAG block, then user message."""
    messages = []
    for h in history:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    template = _load_user_template()
    context_block = template.format(rag_context=rag_context, user_message=user_message)
    messages.append({"role": "user", "content": context_block})
    return messages


def get_system_prompt_with_context(db: Session, org_id: UUID) -> str:
    """Load system template and fill product_name, feedback_count, theme_count, current_date."""
    template = _load_system_prompt()
    product_name = "Unknown product"
    product_description = ""
    if has_product_context(db, org_id):
        try:
            ctx = get_product_context(db, org_id)
            product_name = ctx.product_name or product_name
            product_description = ctx.product_description or ""
        except Exception:
            pass
    feedback_count = db.query(FeedbackItem).filter(FeedbackItem.org_id == org_id).count()
    theme_count = db.query(Theme).filter(Theme.org_id == org_id, Theme.is_current == True).count()
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return template.format(
        product_name=product_name,
        product_description=product_description,
        feedback_count=feedback_count,
        theme_count=theme_count,
        current_date=current_date,
    )


def manage_context_window(
    system_prompt: str,
    history: list[dict],
    rag_context: str,
    user_message: str,
    tools_prompt_len: int = 0,
) -> tuple[str, list[dict], str]:
    """
    Estimate tokens; if over budget apply fallbacks: reduce history to 10, RAG to 10 items, themes to 3, truncate content.
    Returns (system_prompt, history, rag_context) possibly truncated.
    """
    budget = TOKEN_BUDGET - RESPONSE_BUDGET - estimate_token_count(user_message) - tools_prompt_len
    used = estimate_token_count(system_prompt) + sum(estimate_token_count(m.get("content", "")) for m in history) + estimate_token_count(rag_context)
    if used <= budget:
        return system_prompt, history, rag_context
    if len(history) > 10:
        history = history[-10:]
    used = estimate_token_count(system_prompt) + sum(estimate_token_count(m.get("content", "")) for m in history) + estimate_token_count(rag_context)
    if used > budget and "--- Relevant feedback ---" in rag_context:
        before, _, after = rag_context.partition("--- Top themes ---")
        before_head, _, feedback_block = before.partition("--- Relevant feedback ---")
        lines = feedback_block.strip().split("\n")[:10]
        rag_context = before_head + "--- Relevant feedback ---\n" + "\n".join(lines) + "\n--- Top themes ---" + after
    if estimate_token_count(rag_context) > budget // 2:
        rag_context = truncate_context(rag_context, budget // 2, reduce_feedback_to_chars=100)
    return system_prompt, history, rag_context
