"""Generate individual brief sections via LLM (Phase 7). Uses brief_prompts_loader and call_brief_llm."""

import json
from app.prompts.brief_prompts_loader import get_section_templates, get_solution_evaluation_template
from app.services import llm_chat
from app.utils.logging import get_logger

logger = get_logger(__name__)

SECTION_TITLES = {
    "problem_statement": "Problem Statement",
    "customer_impact": "Customer Impact",
    "evidence_summary": "Evidence Summary",
    "trend_analysis": "Trend Analysis",
    "business_case": "Business Case",
    "recommended_action": "Recommended Action",
    "risks": "Risks & Considerations",
}

FAILED_PLACEHOLDER = "[Generation failed — click to retry]"


def _safe_format(template: str, **kwargs: str) -> str:
    """Format template; use empty string for missing keys."""
    for k, v in kwargs.items():
        if v is None:
            kwargs[k] = ""
    return template.format(**{k: (v or "") for k, v in kwargs.items()})


def generate_problem_statement(theme_data: dict, feedback_items: list) -> str:
    """Generate Problem Statement section."""
    quotes = "\n".join(
        f'- "{item.get("verbatim_quote") or item.get("content", "")[:200]}"'
        for item in feedback_items[:10]
    )
    pain_points = ", ".join({str(item.get("pain_point") or "") for item in feedback_items if item.get("pain_point")})
    return _call_brief_llm_for_section(
        "problem_statement",
        theme_name=theme_data.get("name", ""),
        theme_description=theme_data.get("description") or "",
        pain_points=pain_points[:1000],
        quotes=quotes[:4000],
    )


def _call_brief_llm_for_section(template_key: str, **kwargs: str) -> str:
    """Fill section template and call brief LLM (uses brief_* settings)."""
    templates = get_section_templates()
    user = _safe_format(templates[template_key], **kwargs)
    return llm_chat.call_brief_llm(
        "You are a product analyst writing an evidence brief. Output only the section text, no labels.",
        user,
    )


def generate_customer_impact(theme_data: dict, customers: list) -> str:
    """Generate Customer Impact section."""
    import json as _json
    segment_breakdown = _json.dumps(theme_data.get("segment_breakdown") or {}, indent=0)
    urgency_breakdown = _json.dumps(theme_data.get("urgency_breakdown") or {}, indent=0)
    customer_list = "\n".join(f"- {c.get('company_name') or c.get('domain')} ({c.get('segment') or 'N/A'})" for c in customers[:50])
    return _call_brief_llm_for_section(
        "customer_impact",
        theme_name=theme_data.get("name", ""),
        segment_breakdown=segment_breakdown,
        unique_customers=str(theme_data.get("unique_customers", 0)),
        urgency_breakdown=urgency_breakdown,
        customer_list=customer_list or "No matched customers.",
    )


def generate_evidence_summary(theme_data: dict, feedback_items: list) -> str:
    """Generate Evidence Summary section."""
    lines = []
    for item in feedback_items[:20]:
        q = (item.get("verbatim_quote") or item.get("content") or "")[:300]
        topic = item.get("topic") or ""
        pain = item.get("pain_point") or ""
        lines.append(f"[{topic}] {pain}\nQuote: {q}")
    quotes_with_metadata = "\n\n".join(lines) or "No quotes."
    return _call_brief_llm_for_section(
        "evidence_summary",
        theme_name=theme_data.get("name", ""),
        quotes_with_metadata=quotes_with_metadata[:6000],
    )


def generate_trend_analysis(theme_data: dict, feedback_items: list) -> str:
    """Generate Trend Analysis section."""
    from collections import Counter
    timestamps = [item.get("created_at") for item in feedback_items if item.get("created_at")]
    by_month = Counter(str(t)[:7] for t in timestamps) if timestamps else {}
    timestamp_summary = str(dict(by_month)) if by_month else "No timestamp data."
    urgency_escalation = str(theme_data.get("urgency_breakdown") or "N/A")
    return _call_brief_llm_for_section(
        "trend_analysis",
        theme_name=theme_data.get("name", ""),
        timestamp_summary=timestamp_summary,
        urgency_escalation=urgency_escalation,
    )


def generate_business_case(theme_data: dict, scoring_config: dict | None, product_context: dict | None) -> str:
    """Generate Business Case section."""
    import json as _json
    score_breakdown = _json.dumps(theme_data.get("score_breakdown") or {}, indent=0)
    segment_breakdown = _json.dumps(theme_data.get("segment_breakdown") or {}, indent=0)
    goals = (product_context or {}).get("target_users") or (scoring_config or {}).get("goals") or []
    product_goals = str(goals) if isinstance(goals, list) else str(goals)
    return _call_brief_llm_for_section(
        "business_case",
        theme_name=theme_data.get("name", ""),
        priority_score=str(theme_data.get("priority_score", 0)),
        score_breakdown=score_breakdown,
        product_goals=product_goals,
        segment_breakdown=segment_breakdown,
        unique_customers=str(theme_data.get("unique_customers", 0)),
    )


def generate_recommended_action(theme_data: dict, feedback_items: list, product_context: dict | None) -> str:
    """Generate Recommended Action section."""
    pain_points = ", ".join({str(f.get("pain_point") or "") for f in feedback_items if f.get("pain_point")})[:1500]
    feature_gaps = ", ".join({str(f.get("feature_gap") or "") for f in feedback_items if f.get("feature_gap")})[:1000]
    ctx = product_context or {}
    product_context_str = f"Name: {ctx.get('product_name')}. Description: {ctx.get('product_description')}. Limitations: {ctx.get('known_limitations') or []}"
    return _call_brief_llm_for_section(
        "recommended_action",
        theme_name=theme_data.get("name", ""),
        theme_description=theme_data.get("description") or "",
        pain_points=pain_points or "N/A",
        feature_gaps=feature_gaps or "N/A",
        product_context=product_context_str,
    )


def generate_risks(theme_data: dict, feedback_items: list, all_themes: list) -> str:
    """Generate Risks & Considerations section."""
    import json as _json
    sentiment_breakdown = _json.dumps(theme_data.get("sentiment_breakdown") or {}, indent=0)
    conflicting_feedback = "N/A"
    related_themes = ", ".join(t.get("name", "") for t in (all_themes or [])[:5])
    return _call_brief_llm_for_section(
        "risks",
        theme_name=theme_data.get("name", ""),
        sentiment_breakdown=sentiment_breakdown,
        conflicting_feedback=conflicting_feedback,
        related_themes=related_themes or "N/A",
    )


def evaluate_solution_against_evidence(
    theme_data: dict, feedback_items: list, solution_description: str
) -> dict:
    """Run solution evaluation; return parsed JSON with pain_points_addressed, coverage_score, etc."""
    pain_points = list({str(f.get("pain_point") or "") for f in feedback_items if f.get("pain_point")})
    feature_gaps = list({str(f.get("feature_gap") or "") for f in feedback_items if f.get("feature_gap")})
    import json as _json
    segment_breakdown = _json.dumps(theme_data.get("segment_breakdown") or {}, indent=0)
    template = get_solution_evaluation_template()
    user = _safe_format(
        template,
        theme_name=theme_data.get("name", ""),
        theme_description=theme_data.get("description") or "",
        pain_points=_json.dumps(pain_points),
        feature_gaps=_json.dumps(feature_gaps),
        segment_breakdown=segment_breakdown,
        solution_description=solution_description[:8000],
    )
    raw = llm_chat.call_brief_llm(
        "You are a product analyst. Respond with a single JSON object only, no markdown.",
        user,
    )
    stripped = raw.strip()
    for prefix in ("```json", "```"):
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):].strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
    out = json.loads(stripped)
    if "coverage_score" in out and not isinstance(out["coverage_score"], (int, float)):
        out["coverage_score"] = 0.0
    if "predicted_impact_score" in out and not isinstance(out["predicted_impact_score"], (int, float)):
        out["predicted_impact_score"] = 0.0
    return out
