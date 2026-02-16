"""Individual tool implementations for chat (Phase 6)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.feedback_item import FeedbackItem
from app.models.theme import Theme
from app.services import embedding_service
from app.services.rag_service import format_feedback_context, format_theme_context, format_stats_context


def _theme_to_dict(t: Theme) -> dict:
    """Serialize theme for tool result."""
    return {
        "id": str(t.id),
        "name": t.name,
        "description": t.description,
        "mention_count": t.mention_count,
        "unique_customers": t.unique_customers,
        "priority_score": t.priority_score,
        "score_breakdown": t.score_breakdown,
        "top_quotes": t.top_quotes,
        "urgency_breakdown": t.urgency_breakdown,
        "sentiment_breakdown": t.sentiment_breakdown,
    }


def _feedback_to_dict(item: FeedbackItem) -> dict:
    """Serialize feedback item for tool result."""
    return {
        "id": str(item.id),
        "content": (item.content or "")[:500],
        "pain_point": item.pain_point,
        "topic": item.topic,
        "urgency": item.urgency,
        "sentiment": item.sentiment,
        "customer_name": item.customer_name,
        "segment": item.segment,
        "source_type": item.source_type,
        "verbatim_quote": (item.verbatim_quote or "")[:300],
    }


def search_feedback_tool(db: Session, org_id: UUID, params: dict) -> dict:
    """Embed query, pgvector search, apply filters. Returns list of feedback items."""
    query = (params.get("query") or "").strip()
    limit = min(int(params.get("limit") or 10), 50)
    filters = {}
    if params.get("segment"):
        filters["segment"] = params["segment"]
    if params.get("urgency"):
        filters["urgency"] = params["urgency"]
    if params.get("source_type"):
        filters["source_type"] = params["source_type"]
    if not query:
        return {"items": [], "message": "Query is required."}
    emb = embedding_service.generate_embedding(query)
    if not emb:
        return {"items": [], "message": "Could not generate embedding."}
    from app.services.rag_service import retrieve_relevant_feedback
    items = retrieve_relevant_feedback(db, org_id, emb, limit=limit, filters=filters or None)
    theme_ids = [i.theme_id for i in items if i.theme_id]
    theme_id_to_name = {}
    if theme_ids:
        themes = db.query(Theme).filter(Theme.id.in_(theme_ids), Theme.org_id == org_id).all()
        theme_id_to_name = {t.id: t.name for t in themes}
    return {"items": [_feedback_to_dict(i) for i in items], "context": format_feedback_context(items, theme_id_to_name)}


def get_theme_tool(db: Session, org_id: UUID, params: dict) -> dict:
    """Look up theme by ID (exact) or name (ILIKE %name%)."""
    theme_id = params.get("theme_id")
    theme_name = (params.get("theme_name") or "").strip()
    if theme_id:
        try:
            uid = UUID(theme_id)
            theme = db.query(Theme).filter(Theme.org_id == org_id, Theme.id == uid).first()
            if theme:
                return {"theme": _theme_to_dict(theme)}
            return {"error": "Theme not found."}
        except ValueError:
            return {"error": "Invalid theme_id."}
    if theme_name:
        theme = db.query(Theme).filter(Theme.org_id == org_id, Theme.is_current == True).filter(
            Theme.name.ilike(f"%{theme_name}%")
        ).first()
        if theme:
            return {"theme": _theme_to_dict(theme)}
        return {"error": "No theme matching that name."}
    return {"error": "Provide theme_id or theme_name."}


def list_themes_tool(db: Session, org_id: UUID, params: dict) -> dict:
    """Current themes sorted by sort_by, limited."""
    sort_by = params.get("sort_by") or "priority_score"
    limit = min(int(params.get("limit") or 10), 50)
    col = getattr(Theme, sort_by, Theme.priority_score)
    themes = (
        db.query(Theme)
        .filter(Theme.org_id == org_id, Theme.is_current == True)
        .order_by(col.desc().nullslast())
        .limit(limit)
        .all()
    )
    return {"themes": [_theme_to_dict(t) for t in themes], "summary": format_theme_context(db, org_id, limit)}


def compare_segments_tool(db: Session, org_id: UUID, params: dict) -> dict:
    """Per-segment: count, top themes, urgency breakdown, sentiment breakdown."""
    segments = params.get("segments") or []
    topic = (params.get("topic") or "").strip()
    if not segments:
        return {"error": "segments list required (e.g. [\"enterprise\", \"smb\"])."}
    result = {}
    for seg in segments:
        q = db.query(FeedbackItem).filter(FeedbackItem.org_id == org_id, FeedbackItem.segment == seg)
        if topic:
            q = q.filter(FeedbackItem.topic.ilike(f"%{topic}%"))
        count = q.count()
        items = q.limit(100).all()
        urgency_breakdown = {}
        sentiment_breakdown = {}
        for i in items:
            u = i.urgency or "unknown"
            urgency_breakdown[u] = urgency_breakdown.get(u, 0) + 1
            s = i.sentiment or "unknown"
            sentiment_breakdown[s] = sentiment_breakdown.get(s, 0) + 1
        theme_ids = [i.theme_id for i in items if i.theme_id]
        top_themes = []
        if theme_ids:
            from collections import Counter
            c = Counter(theme_ids)
            for tid, _ in c.most_common(5):
                t = db.query(Theme).filter(Theme.id == tid, Theme.org_id == org_id).first()
                if t:
                    top_themes.append({"name": t.name, "count": c[tid]})
        result[seg] = {
            "count": count,
            "top_themes": top_themes,
            "urgency_breakdown": urgency_breakdown,
            "sentiment_breakdown": sentiment_breakdown,
        }
    return {"segments": result}


def get_customer_feedback_tool(db: Session, org_id: UUID, params: dict) -> dict:
    """Look up customer by name or ID, return customer info and their feedback."""
    customer_id = params.get("customer_id")
    customer_name = (params.get("customer_name") or "").strip()
    limit = min(int(params.get("limit") or 10), 50)
    customer = None
    if customer_id:
        try:
            uid = UUID(customer_id)
            customer = db.query(Customer).filter(Customer.org_id == org_id, Customer.id == uid).first()
        except ValueError:
            pass
    if not customer and customer_name:
        customer = db.query(Customer).filter(
            Customer.org_id == org_id,
            Customer.company_name.ilike(f"%{customer_name}%"),
        ).first()
    if not customer:
        return {"error": "Customer not found."}
    items = (
        db.query(FeedbackItem)
        .filter(FeedbackItem.org_id == org_id, FeedbackItem.customer_id == customer.id)
        .order_by(FeedbackItem.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "customer": {"id": str(customer.id), "company_name": customer.company_name, "domain": customer.domain, "segment": customer.segment},
        "feedback": [_feedback_to_dict(i) for i in items],
    }


def get_stats_tool(db: Session, org_id: UUID, params: dict) -> dict:
    """Aggregate dashboard stats."""
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
    from app.services.customer_service import get_top_customers
    top = get_top_customers(db, org_id, limit=5)
    top_customers = [{"company_name": c.company_name, "domain": c.domain, "feedback_count": n} for c, n in top]
    return {
        "total_feedback": total,
        "by_source": dict(by_source),
        "by_extraction_status": dict(by_status),
        "theme_count": theme_count,
        "top_customers": top_customers,
        "summary": format_stats_context(db, org_id),
    }


def filter_feedback_tool(db: Session, org_id: UUID, params: dict) -> dict:
    """Multi-criteria filter on feedback."""
    limit = min(int(params.get("limit") or 20), 100)
    q = db.query(FeedbackItem).filter(FeedbackItem.org_id == org_id)
    if params.get("segment"):
        q = q.filter(FeedbackItem.segment == params["segment"])
    if params.get("urgency"):
        q = q.filter(FeedbackItem.urgency == params["urgency"])
    if params.get("sentiment"):
        q = q.filter(FeedbackItem.sentiment == params["sentiment"])
    if params.get("source_type"):
        q = q.filter(FeedbackItem.source_type == params["source_type"])
    if params.get("theme"):
        theme = db.query(Theme).filter(Theme.org_id == org_id, Theme.name.ilike(f"%{params['theme']}%")).first()
        if theme:
            q = q.filter(FeedbackItem.theme_id == theme.id)
    if params.get("date_from"):
        try:
            q = q.filter(FeedbackItem.created_at >= datetime.fromisoformat(params["date_from"].replace("Z", "+00:00")))
        except ValueError:
            pass
    if params.get("date_to"):
        try:
            q = q.filter(FeedbackItem.created_at <= datetime.fromisoformat(params["date_to"].replace("Z", "+00:00")))
        except ValueError:
            pass
    items = q.order_by(FeedbackItem.created_at.desc()).limit(limit).all()
    theme_ids = [i.theme_id for i in items if i.theme_id]
    theme_id_to_name = {}
    if theme_ids:
        themes = db.query(Theme).filter(Theme.id.in_(theme_ids), Theme.org_id == org_id).all()
        theme_id_to_name = {t.id: t.name for t in themes}
    return {"items": [_feedback_to_dict(i) for i in items], "count": len(items), "context": format_feedback_context(items, theme_id_to_name)}


def generate_brief_tool(db: Session, org_id: UUID, params: dict, user_id: UUID | None = None) -> dict:
    """Start brief generation for a theme; return link to brief. Requires user_id for created_by."""
    if not user_id:
        return {"error": "User context required to generate a brief."}
    theme_id = params.get("theme_id")
    theme_name = (params.get("theme_name") or "").strip()
    theme = None
    if theme_id:
        try:
            uid = UUID(theme_id)
            theme = db.query(Theme).filter(Theme.org_id == org_id, Theme.id == uid).first()
        except ValueError:
            pass
    if not theme and theme_name:
        theme = db.query(Theme).filter(
            Theme.org_id == org_id, Theme.is_current == True, Theme.name.ilike(f"%{theme_name}%")
        ).first()
    if not theme:
        return {"error": "Theme not found. Provide theme_id or theme_name."}
    from app.services import brief_service
    from app.config import settings
    brief_id = brief_service.generate_brief(db, org_id, theme.id, user_id)
    if not brief_id:
        return {"error": "Could not start brief generation."}
    base = getattr(settings, "frontend_url", "http://localhost:3000")
    link = f"{base.rstrip('/')}/briefs/{brief_id}"
    return {"message": f"Brief generation started.", "brief_id": str(brief_id), "link": link}


def generate_spec_tool(
    db: Session, org_id: UUID, params: dict, user_id: UUID | None = None
) -> dict:
    """Start spec generation for a brief (must have solution evaluation). Resolve brief via theme or brief_id."""
    if not user_id:
        return {"error": "User context required to generate a spec."}
    from app.services import spec_service
    from app.config import settings

    brief_id = params.get("brief_id")
    theme_id = params.get("theme_id")
    theme_name = (params.get("theme_name") or "").strip()
    scope = (params.get("scope") or "full").lower()
    target_audience = (params.get("target_audience") or "mixed").lower()

    brief = None
    if brief_id:
        try:
            from app.models.brief import Brief
            bid = UUID(brief_id)
            brief = db.query(Brief).filter(Brief.id == bid, Brief.org_id == org_id).first()
        except ValueError:
            pass
    if not brief and (theme_id or theme_name):
        theme = None
        if theme_id:
            try:
                tid = UUID(theme_id)
                theme = db.query(Theme).filter(Theme.org_id == org_id, Theme.id == tid).first()
            except ValueError:
                pass
        if not theme and theme_name:
            theme = db.query(Theme).filter(
                Theme.org_id == org_id,
                Theme.is_current == True,
                Theme.name.ilike(f"%{theme_name}%"),
            ).first()
        if theme:
            from app.services import brief_service
            brief = brief_service.get_current_brief(db, org_id, theme.id)
    if not brief:
        return {"error": "Brief not found. Provide brief_id or theme_id/theme_name with an existing brief."}
    if not (brief.solution_evaluation and isinstance(brief.solution_evaluation, dict)):
        return {"error": "This brief has no solution evaluation. Evaluate a solution on the brief page first."}
    spec_id = spec_service.generate_spec(
        db, org_id, brief.id, user_id, scope, target_audience, None
    )
    if not spec_id:
        return {"error": "Could not start spec generation."}
    base = getattr(settings, "frontend_url", "http://localhost:3000")
    link = f"{base.rstrip('/')}/specs/{spec_id}"
    return {"message": "Spec generation started.", "spec_id": str(spec_id), "link": link}


def get_spec_section_tool(db: Session, org_id: UUID, params: dict) -> dict:
    """Return a section of a spec (e.g. user_stories). Resolve spec by spec_id or theme."""
    from app.services import spec_service
    from app.services import brief_service

    spec_id = params.get("spec_id")
    theme_id = params.get("theme_id")
    theme_name = (params.get("theme_name") or "").strip()
    section_key = (params.get("section_key") or "user_stories").strip()

    spec = None
    if spec_id:
        try:
            sid = UUID(spec_id)
            spec = spec_service.get_spec(db, org_id, sid)
        except ValueError:
            pass
    if not spec and (theme_id or theme_name):
        theme = None
        if theme_id:
            try:
                tid = UUID(theme_id)
                theme = db.query(Theme).filter(Theme.org_id == org_id, Theme.id == tid).first()
            except ValueError:
                pass
        if not theme and theme_name:
            theme = db.query(Theme).filter(
                Theme.org_id == org_id,
                Theme.is_current == True,
                Theme.name.ilike(f"%{theme_name}%"),
            ).first()
        if theme:
            brief = brief_service.get_current_brief(db, org_id, theme.id)
            if brief:
                spec = spec_service.get_current_spec(db, org_id, brief.id)
    if not spec:
        return {"error": "Spec not found. Provide spec_id or theme_id/theme_name with an existing spec."}
    for s in (spec.sections or []):
        if s.get("key") == section_key:
            return {
                "section_key": section_key,
                "title": s.get("title", section_key),
                "content": s.get("content") or "",
            }
    return {"error": f"Section '{section_key}' not found in this spec."}
