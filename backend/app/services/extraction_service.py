"""
Extraction of structured signals from feedback via LLM. Uses product context when available.
"""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.feedback_item import FeedbackItem
from app.services.llm_service import call_llm
from app.services.product_context_service import get_product_context
from app.utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load_system_prompt() -> str:
    path = _PROMPTS_DIR / "extraction.txt"
    return path.read_text().strip()


def _load_user_prompt_template() -> str:
    path = _PROMPTS_DIR / "extraction_user.txt"
    return path.read_text().strip()


def build_extraction_prompt(feedback_content: str, product_context: object | None) -> str:
    """
    Build the user prompt for extraction. If product_context is None, include the exact
    fallback text (GAP 3). Otherwise include name, description, features, limitations.
    """
    if product_context is None:
        product_context_section = (
            "No product context provided. Extract signals based on the feedback text alone."
        )
    else:
        parts = [
            f"Product: {getattr(product_context, 'product_name', '')}",
            f"Description: {getattr(product_context, 'product_description', '')}",
        ]
        features = getattr(product_context, "existing_features", None) or []
        if features:
            parts.append("Existing features: " + ", ".join(features))
        limitations = getattr(product_context, "known_limitations", None) or []
        if limitations:
            parts.append("Known limitations: " + ", ".join(limitations))
        target = getattr(product_context, "target_users", None)
        if target:
            parts.append(f"Target users: {target}")
        extra = getattr(product_context, "additional_context", None)
        if extra:
            parts.append(f"Additional context: {extra}")
        product_context_section = "\n".join(parts)

    return _load_user_prompt_template().format(
        product_context_section=product_context_section,
        feedback_content=feedback_content,
    )


def _normalize_extraction_result(result: dict) -> None:
    """
    Normalize LLM output in place so validation accepts common variations:
    urgency/sentiment casing, string booleans, string confidence, strip strings.
    """
    if isinstance(result.get("pain_point"), str):
        result["pain_point"] = result["pain_point"].strip()
    if isinstance(result.get("topic"), str):
        result["topic"] = result["topic"].strip()
    u = result.get("urgency")
    if isinstance(u, str) and u.strip():
        result["urgency"] = u.strip().lower()
    s = result.get("sentiment")
    if isinstance(s, str) and s.strip():
        result["sentiment"] = s.strip().lower()
    ie = result.get("is_existing_feature")
    if isinstance(ie, str):
        result["is_existing_feature"] = ie.strip().lower() in ("true", "1", "yes")
    elif ie in (1, 0):
        result["is_existing_feature"] = bool(ie)
    c = result.get("confidence")
    if isinstance(c, str) and c.strip():
        try:
            result["confidence"] = float(c)
        except ValueError:
            pass


def validate_extraction_result(result: dict) -> bool:
    """
    Validate LLM output. Returns True if valid.
    Required: pain_point, topic non-empty; urgency in enum; sentiment in enum;
    is_existing_feature bool; confidence in [0, 1].
    """
    pain = result.get("pain_point")
    if not isinstance(pain, str) or not pain.strip():
        return False
    topic = result.get("topic")
    if not isinstance(topic, str) or not topic.strip():
        return False
    urgency = result.get("urgency")
    if urgency not in ("low", "medium", "high", "critical"):
        return False
    sentiment = result.get("sentiment")
    if sentiment not in ("positive", "neutral", "negative"):
        return False
    is_existing = result.get("is_existing_feature")
    if not isinstance(is_existing, bool):
        return False
    confidence = result.get("confidence")
    if confidence is not None and (
        not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1)
    ):
        return False
    return True


def extract_signals(db: Session, feedback_item_id: UUID, org_id: UUID) -> None:
    """
    Load feedback item, run LLM extraction (temperature=0), validate, update item or set failed.
    Skips if extraction_status is already "completed". Always stores raw_llm_response.
    """
    item = db.query(FeedbackItem).filter(
        FeedbackItem.id == feedback_item_id,
        FeedbackItem.org_id == org_id,
    ).first()
    if item is None:
        raise NotFoundError("Feedback item not found.")
    if item.extraction_status == "completed":
        return

    product_context = None
    try:
        product_context = get_product_context(db, org_id)
    except NotFoundError:
        pass

    system_prompt = _load_system_prompt()
    user_prompt = build_extraction_prompt(item.content, product_context)

    try:
        result, raw_response = call_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            expected_schema=None,
            temperature=0,
            max_tokens=1024,
        )
    except Exception as e:
        logger.exception("Extraction LLM call failed", extra={"feedback_id": str(feedback_item_id), "org_id": str(org_id)})
        item.extraction_status = "failed"
        item.raw_llm_response = str(e)[:10000] if str(e) else None
        db.commit()
        return

    item.raw_llm_response = raw_response

    _normalize_extraction_result(result)
    if not validate_extraction_result(result):
        item.extraction_status = "failed"
        db.commit()
        logger.warning(
            "Extraction validation failed",
            extra={"feedback_id": str(feedback_item_id), "raw_preview": raw_response[:500]},
        )
        return

    item.pain_point = (result.get("pain_point") or "").strip() or None
    item.topic = (result.get("topic") or "").strip() or None
    item.related_feature = (result.get("related_feature") or "").strip() or None
    item.is_existing_feature = result.get("is_existing_feature")
    item.feature_gap = (result.get("feature_gap") or "").strip() if result.get("feature_gap") else None
    item.urgency = (result.get("urgency") or "").strip() or None
    item.sentiment = (result.get("sentiment") or "").strip() or None
    item.verbatim_quote = (result.get("verbatim_quote") or "").strip() or None
    item.extraction_confidence = float(result.get("confidence", 0))
    item.extraction_status = "completed"
    item.extracted_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(
        "Extraction completed",
        extra={
            "feedback_id": str(feedback_item_id),
            "org_id": str(org_id),
            "extraction_status": "completed",
            "confidence": item.extraction_confidence,
        },
    )


def get_extraction_stats(db: Session, org_id: UUID) -> dict:
    """Return total, pending, completed, failed counts for org feedback items."""
    from sqlalchemy import func

    q = db.query(FeedbackItem.extraction_status, func.count(FeedbackItem.id)).filter(
        FeedbackItem.org_id == org_id
    ).group_by(FeedbackItem.extraction_status)
    counts = dict(q.all())
    total = sum(counts.values())
    return {
        "total": total,
        "pending": counts.get("pending", 0),
        "completed": counts.get("completed", 0),
        "failed": counts.get("failed", 0),
    }
