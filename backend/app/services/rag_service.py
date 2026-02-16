"""RAG retrieval and context formatting for chat (Phase 6)."""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.feedback_item import FeedbackItem
from app.models.theme import Theme
from app.services import embedding_service

CONTENT_TRUNCATE = 200
TOKEN_BUDGET_TOTAL = 12000
TOKEN_BUDGET_RESPONSE = 4000


def retrieve_relevant_feedback(
    db: Session,
    org_id: UUID,
    query_embedding: list[float],
    limit: int = 20,
    filters: dict | None = None,
) -> list[FeedbackItem]:
    """
    Return feedback items ordered by cosine similarity. embedding_service.get_similar_items
    has no filter support; we fetch more then post-filter by segment/urgency/source_type.
    """
    fetch_limit = limit * 3 if filters else limit
    items = embedding_service.get_similar_items(db, org_id, query_embedding, limit=fetch_limit)
    if not filters:
        return items[:limit]
    out = []
    segment = filters.get("segment")
    urgency = filters.get("urgency")
    source_type = filters.get("source_type")
    for item in items:
        if segment and getattr(item, "segment", None) != segment:
            continue
        if urgency and getattr(item, "urgency", None) != urgency:
            continue
        if source_type and getattr(item, "source_type", None) != source_type:
            continue
        out.append(item)
        if len(out) >= limit:
            break
    return out


def format_feedback_context(items: list, theme_id_to_name: dict | None = None) -> str:
    """Format feedback items into a concise string for LLM context (content truncated 200 chars)."""
    lines = []
    for i, item in enumerate(items, 1):
        content = (item.content or "")[:CONTENT_TRUNCATE]
        if len(item.content or "") > CONTENT_TRUNCATE:
            content += "..."
        pain = getattr(item, "pain_point", None) or ""
        topic = getattr(item, "topic", None) or ""
        urgency = getattr(item, "urgency", None) or ""
        sentiment = getattr(item, "sentiment", None) or ""
        customer_name = getattr(item, "customer_name", None) or ""
        segment = getattr(item, "segment", None) or ""
        theme_name = ""
        tid = getattr(item, "theme_id", None)
        if theme_id_to_name and tid:
            theme_name = theme_id_to_name.get(tid) or "(theme)"
        elif hasattr(item, "theme") and item.theme:
            theme_name = item.theme.name or ""
        elif tid:
            theme_name = "(theme)"
        quote = getattr(item, "verbatim_quote", None) or ""
        lines.append(
            f"[{i}] content: {content} | pain_point: {pain} | topic: {topic} | "
            f"urgency: {urgency} | sentiment: {sentiment} | customer: {customer_name} | "
            f"segment: {segment} | theme: {theme_name} | quote: {(quote or '')[:150]}"
        )
    return "\n".join(lines) if lines else "No feedback items."


def format_theme_context(db: Session, org_id: UUID, limit: int = 5) -> str:
    """Top current themes with name, mention_count, priority_score."""
    themes = (
        db.query(Theme)
        .filter(Theme.org_id == org_id, Theme.is_current == True)
        .order_by(Theme.priority_score.desc().nullslast())
        .limit(limit)
        .all()
    )
    lines = []
    for t in themes:
        lines.append(f"- {t.name}: mentions={t.mention_count}, priority_score={t.priority_score}")
    return "\n".join(lines) if lines else "No themes."


def format_stats_context(db: Session, org_id: UUID) -> str:
    """Totals, by source, by status, theme count, extraction/enrichment stats."""
    total = db.query(FeedbackItem).filter(FeedbackItem.org_id == org_id).count()
    by_source = (
        db.query(FeedbackItem.source_type, func.count(FeedbackItem.id))
        .filter(FeedbackItem.org_id == org_id)
        .group_by(FeedbackItem.source_type)
        .all()
    )
    by_status = (
        db.query(FeedbackItem.extraction_status, func.count(FeedbackItem.id))
        .filter(FeedbackItem.org_id == org_id)
        .group_by(FeedbackItem.extraction_status)
        .all()
    )
    theme_count = db.query(Theme).filter(Theme.org_id == org_id, Theme.is_current == True).count()
    extracted = db.query(FeedbackItem).filter(
        FeedbackItem.org_id == org_id, FeedbackItem.extraction_status == "completed"
    ).count()
    matched = db.query(FeedbackItem).filter(
        FeedbackItem.org_id == org_id, FeedbackItem.match_status == "matched"
    ).count()
    parts = [f"Total feedback: {total}", f"Themes: {theme_count}", f"Extracted: {extracted}", f"Matched to customer: {matched}"]
    if by_source:
        parts.append("By source: " + ", ".join(f"{s}={c}" for s, c in by_source))
    if by_status:
        parts.append("By extraction status: " + ", ".join(f"{s}={c}" for s, c in by_status))
    return ". ".join(parts)


def estimate_token_count(text: str) -> int:
    """Rough token estimate: chars / 4."""
    if not text:
        return 0
    return max(0, len(text) // 4)


def truncate_context(
    context: str,
    max_tokens: int,
    *,
    reduce_feedback_to_chars: int | None = None,
) -> str:
    """
    If context exceeds max_tokens, truncate. Optionally truncate each feedback line
    more aggressively via reduce_feedback_to_chars (e.g. 100 per item).
    """
    current = estimate_token_count(context)
    if current <= max_tokens:
        return context
    if reduce_feedback_to_chars:
        lines = context.split("\n")
        out = []
        for line in lines:
            if line.startswith("["):
                idx = line.find("|")
                prefix = (line[: idx + 2] if idx >= 0 else line[: reduce_feedback_to_chars])
                rest = line[len(prefix) :]
                out.append(prefix + rest[: reduce_feedback_to_chars] + ("..." if len(rest) > reduce_feedback_to_chars else ""))
            else:
                out.append(line[: reduce_feedback_to_chars * 2] + ("..." if len(line) > reduce_feedback_to_chars * 2 else ""))
        context = "\n".join(out)
    else:
        context = context[: max_tokens * 4]
    return context
