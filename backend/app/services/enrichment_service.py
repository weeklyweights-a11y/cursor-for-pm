"""
5-step smart matching: exact → saved mapping → LLM fuzzy → confidence route → unmatched.
All operations org-scoped. Single-item failure does not stop others.
"""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import difflib
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.domain_mapping import DomainMapping
from app.models.feedback_item import FeedbackItem
from app.models.match_review import MatchReviewQueue
from app.services.llm_service import call_llm
from app.utils.domain import normalize_domain
from app.utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_HIGH_CONFIDENCE = 0.85
_LOW_CONFIDENCE = 0.5
_MIN_SIMILARITY = 0.3


def extract_domain_from_email(email: str | None) -> str:
    """Extract domain part from email. Returns empty string if no @ or invalid."""
    if not email or not isinstance(email, str):
        return ""
    email = email.strip().lower()
    if "@" in email:
        return normalize_domain(email.split("@", 1)[1])
    return ""


def _load_fuzzy_system_prompt() -> str:
    path = _PROMPTS_DIR / "fuzzy_match_system.txt"
    return path.read_text().strip()


def _load_fuzzy_user_template() -> str:
    path = _PROMPTS_DIR / "fuzzy_match_user.txt"
    return path.read_text().strip()


def find_candidate_customers(
    db: Session,
    org_id: UUID,
    source_domain: str,
    source_company_name: str | None,
    limit: int = 5,
) -> list[Customer]:
    """
    Top N customers by string similarity (domain + company_name). Active only.
    """
    customers = (
        db.query(Customer)
        .filter(Customer.org_id == org_id, Customer.is_active == True)
        .all()
    )
    if not customers:
        return []
    scored = []
    for c in customers:
        domain_score = difflib.SequenceMatcher(
            None, source_domain.lower(), (c.domain or "").lower()
        ).ratio()
        name_a = (source_company_name or "").lower()
        name_b = (c.company_name or "").lower()
        name_score = difflib.SequenceMatcher(None, name_a, name_b).ratio() if (name_a and name_b) else 0.0
        combined = 0.6 * domain_score + 0.4 * name_score
        scored.append((combined, c))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:limit]]


def llm_fuzzy_match(
    source_domain: str,
    source_company_name: str | None,
    candidates: list[Customer],
) -> tuple[int | None, float]:
    """
    One LLM call: pick best candidate or null. Returns (match_index 0-based or None, confidence 0-1).
    """
    if not candidates:
        return None, 0.0
    system_prompt = _load_fuzzy_system_prompt()
    lines = [
        f"{i}. {c.company_name or 'N/A'} ({c.domain})"
        for i, c in enumerate(candidates)
    ]
    candidates_block = "\n".join(lines)
    user_prompt = _load_fuzzy_user_template().format(
        source_domain=source_domain,
        source_company_name=source_company_name or "N/A",
        candidates_block=candidates_block,
    )
    try:
        result, _ = call_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0,
            max_tokens=128,
        )
    except Exception as e:
        logger.warning(
            "LLM fuzzy match failed",
            extra={"source_domain": source_domain, "error": str(e)[:200]},
        )
        return None, 0.0
    idx = result.get("match_index")
    conf = result.get("confidence")
    if conf is not None and isinstance(conf, (int, float)):
        conf = max(0.0, min(1.0, float(conf)))
    else:
        conf = 0.0
    if idx is None or (isinstance(idx, int) and (idx < 0 or idx >= len(candidates))):
        return None, conf
    if isinstance(idx, int):
        return idx, conf
    return None, conf


def apply_match(
    db: Session,
    feedback_item: FeedbackItem,
    customer: Customer | None,
    match_method: str,
    match_confidence: float,
    match_status: str,
) -> None:
    """Set enrichment fields on feedback item. customer None for unmatched."""
    feedback_item.customer_id = customer.id if customer else None
    feedback_item.customer_domain = customer.domain if customer else None
    feedback_item.customer_name = customer.company_name if customer else None
    feedback_item.segment = customer.segment if customer else None
    feedback_item.match_method = match_method
    feedback_item.match_confidence = match_confidence
    feedback_item.match_status = match_status
    feedback_item.enriched_at = datetime.now(timezone.utc)
    db.flush()


def save_mapping(
    db: Session,
    org_id: UUID,
    source_domain: str,
    source_company_name: str | None,
    customer_id: UUID | None,
    confidence: float,
    match_method: str,
    is_confirmed: bool,
) -> DomainMapping:
    """Create or update domain_mapping for (org_id, source_domain)."""
    existing = (
        db.query(DomainMapping)
        .filter(
            DomainMapping.org_id == org_id,
            DomainMapping.source_domain == source_domain,
        )
        .first()
    )
    if existing:
        existing.source_company_name = source_company_name
        existing.customer_id = customer_id
        existing.confidence = confidence
        existing.match_method = match_method
        existing.is_confirmed = is_confirmed
        db.flush()
        return existing
    mapping = DomainMapping(
        org_id=org_id,
        source_domain=source_domain,
        source_company_name=source_company_name,
        customer_id=customer_id,
        confidence=confidence,
        match_method=match_method,
        is_confirmed=is_confirmed,
    )
    db.add(mapping)
    db.flush()
    return mapping


def _apply_match_to_same_domain_items(
    db: Session,
    org_id: UUID,
    source_domain: str,
    customer: Customer | None,
    match_method: str,
    match_confidence: float,
    match_status: str,
    exclude_feedback_item_id: UUID | None = None,
) -> None:
    """
    Apply the same match to all other feedback items with this source_domain
    (unmatched or pm_review). One LLM call per domain; this cascades to same-domain items.
    """
    candidates = (
        db.query(FeedbackItem)
        .filter(
            FeedbackItem.org_id == org_id,
            FeedbackItem.match_status.in_(("unmatched", "pm_review")),
        )
        .all()
    )
    for other in candidates:
        if exclude_feedback_item_id and other.id == exclude_feedback_item_id:
            continue
        other_domain = extract_domain_from_email(other.author_email) or normalize_domain(
            other.organization_name or ""
        )
        if other_domain == source_domain:
            apply_match(db, other, customer, match_method, match_confidence, match_status)
    db.flush()


def queue_for_review(
    db: Session,
    org_id: UUID,
    feedback_item: FeedbackItem,
    source_domain: str,
    candidate_customer: Customer,
    confidence: float,
) -> MatchReviewQueue:
    """Create match_review_queue entry for PM review."""
    entry = MatchReviewQueue(
        org_id=org_id,
        feedback_item_id=feedback_item.id,
        source_domain=source_domain,
        source_company_name=feedback_item.organization_name,
        candidate_customer_id=candidate_customer.id,
        candidate_customer_name=candidate_customer.company_name,
        candidate_domain=candidate_customer.domain,
        confidence=confidence,
        status="pending",
    )
    db.add(entry)
    db.flush()
    return entry


def enrich_feedback_item(db: Session, org_id: UUID, feedback_item_id: UUID) -> FeedbackItem | None:
    """
    Run 5-step smart matching. Idempotent: skip if already matched/auto_matched.
    Returns updated FeedbackItem or None if not found.
    """
    item = (
        db.query(FeedbackItem)
        .filter(FeedbackItem.id == feedback_item_id, FeedbackItem.org_id == org_id)
        .first()
    )
    if not item:
        return None
    if item.match_status in ("matched", "auto_matched"):
        return item

    source_domain = extract_domain_from_email(item.author_email)
    if not source_domain:
        source_domain = normalize_domain(item.organization_name or "")
    source_company_name = (item.organization_name or "").strip() or None

    if not source_domain:
        logger.info(
            "enrich_feedback_item: no domain (feedback_item_id=%s); marking unmatched",
            str(feedback_item_id),
        )
        apply_match(db, item, None, "unmatched", 0.0, "unmatched")
        db.commit()
        return item

    # Step 1: Exact domain match
    customer = (
        db.query(Customer)
        .filter(
            Customer.org_id == org_id,
            Customer.domain == source_domain,
            Customer.is_active == True,
        )
        .first()
    )
    if customer:
        logger.info(
            "enrich_feedback_item: exact match feedback_item_id=%s domain=%s customer_id=%s",
            str(feedback_item_id), source_domain, str(customer.id),
        )
        apply_match(db, item, customer, "exact", 1.0, "matched")
        save_mapping(db, org_id, source_domain, source_company_name, customer.id, 1.0, "exact", True)
        db.commit()
        return item

    # Step 2: Saved mapping
    mapping = (
        db.query(DomainMapping)
        .filter(
            DomainMapping.org_id == org_id,
            DomainMapping.source_domain == source_domain,
            DomainMapping.is_confirmed == True,
        )
        .first()
    )
    if mapping:
        if mapping.customer_id:
            cust = db.get(Customer, mapping.customer_id)
            if cust:
                apply_match(
                    db, item, cust, "saved_mapping",
                    mapping.confidence or 0.0, "matched",
                )
        else:
            apply_match(db, item, None, "saved_mapping", 0.0, "unmatched")
        db.commit()
        return item

    # Re-check for any mapping (including unconfirmed from a parallel task) to avoid duplicate LLM call.
    any_mapping = (
        db.query(DomainMapping)
        .filter(
            DomainMapping.org_id == org_id,
            DomainMapping.source_domain == source_domain,
        )
        .first()
    )
    if any_mapping:
        if any_mapping.customer_id:
            cust = db.get(Customer, any_mapping.customer_id)
            if cust:
                apply_match(
                    db, item, cust, any_mapping.match_method or "llm_fuzzy",
                    any_mapping.confidence or 0.0, "matched",
                )
        else:
            apply_match(db, item, None, "saved_mapping", 0.0, "unmatched")
        db.commit()
        return item

    # No customers → unmatched
    has_customers = db.query(Customer).filter(Customer.org_id == org_id, Customer.is_active == True).first()
    if not has_customers:
        apply_match(db, item, None, "unmatched", 0.0, "unmatched")
        db.commit()
        return item

    # Step 3: LLM fuzzy
    candidates = find_candidate_customers(db, org_id, source_domain, source_company_name, limit=5)
    if not candidates:
        apply_match(db, item, None, "unmatched", 0.0, "unmatched")
        db.commit()
        return item
    best_score = difflib.SequenceMatcher(
        None, source_domain.lower(), (candidates[0].domain or "").lower()
    ).ratio()
    if best_score < _MIN_SIMILARITY:
        apply_match(db, item, None, "unmatched", 0.0, "unmatched")
        db.commit()
        return item

    match_index, confidence = llm_fuzzy_match(source_domain, source_company_name, candidates)

    # Step 4 & 5: Route by confidence; apply to all same-domain items (domain batching).
    if match_index is not None and confidence >= _HIGH_CONFIDENCE:
        chosen = candidates[match_index]
        apply_match(db, item, chosen, "llm_fuzzy", confidence, "auto_matched")
        save_mapping(db, org_id, source_domain, source_company_name, chosen.id, confidence, "llm_fuzzy", True)
        _apply_match_to_same_domain_items(
            db, org_id, source_domain, chosen, "llm_fuzzy", confidence, "auto_matched",
            exclude_feedback_item_id=item.id,
        )
        db.commit()
        return item
    if match_index is not None and _LOW_CONFIDENCE <= confidence < _HIGH_CONFIDENCE:
        chosen = candidates[match_index]
        apply_match(db, item, chosen, "llm_fuzzy", confidence, "pm_review")
        save_mapping(db, org_id, source_domain, source_company_name, chosen.id, confidence, "llm_fuzzy", False)
        queue_for_review(db, org_id, item, source_domain, chosen, confidence)
        _apply_match_to_same_domain_items(
            db, org_id, source_domain, chosen, "llm_fuzzy", confidence, "pm_review",
            exclude_feedback_item_id=item.id,
        )
        db.commit()
        return item

    apply_match(db, item, None, "unmatched", 0.0, "unmatched")
    db.commit()
    return item


def manual_match_feedback_item(
    db: Session,
    org_id: UUID,
    feedback_item_id: UUID,
    customer_id: UUID,
) -> FeedbackItem | None:
    """
    Manually match a feedback item to a customer. Applies match, saves mapping,
    and cascades to all same-domain unmatched/pm_review items.
    """
    item = (
        db.query(FeedbackItem)
        .filter(
            FeedbackItem.id == feedback_item_id,
            FeedbackItem.org_id == org_id,
        )
        .first()
    )
    if not item:
        return None
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.org_id == org_id,
            Customer.is_active == True,
        )
        .first()
    )
    if not customer:
        return None
    source_domain = extract_domain_from_email(item.author_email) or normalize_domain(
        item.organization_name or ""
    )
    if not source_domain:
        return None
    source_company_name = (item.organization_name or "").strip() or None
    apply_match(db, item, customer, "manual", 1.0, "matched")
    save_mapping(
        db, org_id, source_domain, source_company_name,
        customer.id, 1.0, "manual", True,
    )
    _apply_match_to_same_domain_items(
        db, org_id, source_domain, customer, "manual", 1.0, "matched",
        exclude_feedback_item_id=item.id,
    )
    db.commit()
    db.refresh(item)
    return item


def re_enrich_unmatched(db: Session, org_id: UUID) -> list[tuple[UUID, UUID]]:
    """Return list of (feedback_item_id, org_id) for unmatched items that can be matched by domain.
    Include items with extraction_status=completed OR with author_email/organization_name set
    so matching can run even before extraction finishes.
    """
    from sqlalchemy import and_, or_
    rows = (
        db.query(FeedbackItem.id)
        .filter(
            FeedbackItem.org_id == org_id,
            FeedbackItem.match_status == "unmatched",
            or_(
                FeedbackItem.extraction_status == "completed",
                and_(FeedbackItem.author_email.isnot(None), FeedbackItem.author_email != ""),
                and_(FeedbackItem.organization_name.isnot(None), FeedbackItem.organization_name != ""),
            ),
        )
        .all()
    )
    return [(r[0], org_id) for r in rows]
