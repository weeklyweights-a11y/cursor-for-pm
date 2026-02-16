"""Generate individual spec sections via LLM (Phase 8). Uses spec_prompts_loader and call_spec_llm."""

import json

from app.prompts.spec_prompts_loader import get_section_template
from app.services import llm_chat
from app.utils.logging import get_logger

logger = get_logger(__name__)

SECTION_TITLES = {
    "executive_summary": "Executive Summary",
    "background_evidence": "Background & Evidence",
    "user_stories": "User Stories",
    "functional_requirements": "Functional Requirements",
    "technical_guidance": "Technical Guidance",
    "data_model_changes": "Data Model Changes",
    "api_contracts": "API Contracts",
    "testing_verification": "Testing & Verification",
}

FAILED_PLACEHOLDER = "[Generation failed — click to retry]"


def _safe_format(template: str, **kwargs: str) -> str:
    """Format template; use empty string for missing keys."""
    safe = {k: (v if v is not None else "") for k, v in kwargs.items()}
    for k in list(safe.keys()):
        if safe[k] is None:
            safe[k] = ""
    return template.format(**{k: str(v)[:20000] for k, v in safe.items()})


def _call_spec_llm(section_key: str, **kwargs: str) -> str:
    """Fill section template and call spec LLM."""
    template = get_section_template(section_key)
    user = _safe_format(template, **kwargs)
    return llm_chat.call_spec_llm(
        "You are writing an implementation spec section. Output only the section content, no labels.",
        user,
    )


def generate_executive_summary(brief_data: dict, solution_eval: dict, config: dict) -> str:
    """Generate Executive Summary section."""
    problem = _section_content(brief_data, "problem_statement")
    business = _section_content(brief_data, "business_case")
    coverage = (solution_eval or {}).get("coverage_score", 0)
    sol_desc = (solution_eval or {}).get("solution_description", "") or config.get("solution_description", "")
    return _call_spec_llm(
        "executive_summary",
        theme_name=brief_data.get("theme_name", ""),
        problem_statement=problem,
        business_case=business,
        solution_description=sol_desc,
        coverage_score=str(coverage),
    )


def _section_content(brief_data: dict, key: str) -> str:
    """Get content of a brief section by key."""
    for s in (brief_data.get("sections") or []):
        if s.get("key") == key:
            return s.get("content") or ""
    return ""


def generate_background_evidence(brief_data: dict, theme_data: dict, config: dict) -> str:
    """Generate Background & Evidence section."""
    evidence = _section_content(brief_data, "evidence_summary")
    impact = _section_content(brief_data, "customer_impact")
    quotes = "\n".join(
        f'- {q.get("quote", q) if isinstance(q, dict) else q} — {q.get("customer", "")}'
        for q in (theme_data.get("top_quotes") or [])[:10]
    )
    if not quotes and theme_data.get("feedback_items"):
        for item in (theme_data.get("feedback_items") or [])[:10]:
            q = (item.get("verbatim_quote") or item.get("content") or "")[:300]
            quotes += f'\n- "{q}" — {item.get("customer_name", "N/A")}'
    score_breakdown = json.dumps(theme_data.get("score_breakdown") or {}, indent=0)
    return _call_spec_llm(
        "background_evidence",
        evidence_summary=evidence,
        customer_impact=impact,
        quotes=quotes or "No quotes.",
        priority_score_breakdown=score_breakdown,
    )


def generate_user_stories(solution_eval: dict, theme_data: dict, config: dict) -> str:
    """Generate User Stories section."""
    pain_points = json.dumps((solution_eval or {}).get("pain_points_addressed") or [], indent=0)
    gaps = json.dumps((solution_eval or {}).get("gaps") or [], indent=0)
    product_ctx = _str_dict((theme_data or {}).get("product_context") or config.get("product_context") or {})
    sol_desc = (solution_eval or {}).get("solution_description", "") or config.get("solution_description", "")
    scope = (config or {}).get("scope", "full")
    return _call_spec_llm(
        "user_stories",
        scope=scope,
        solution_description=sol_desc or "N/A",
        pain_points_addressed=pain_points,
        feature_gaps=gaps,
        product_context=product_ctx,
    )


def _str_dict(d: dict) -> str:
    """Serialize dict for prompt."""
    if not d:
        return ""
    return json.dumps(d, indent=0)[:4000]


def generate_functional_requirements(user_stories_content: str, brief_data: dict, config: dict) -> str:
    """Generate Functional Requirements section."""
    product_ctx = _str_dict((config or {}).get("product_context") or {})
    sol_desc = (config or {}).get("solution_description", "")
    return _call_spec_llm(
        "functional_requirements",
        user_stories=user_stories_content or "N/A",
        product_context=product_ctx,
        solution_description=sol_desc,
    )


def generate_technical_guidance(
    functional_requirements_content: str, product_context: dict, config: dict
) -> str:
    """Generate Technical Guidance section."""
    scope = (config or {}).get("scope", "full")
    audience = (config or {}).get("target_audience", "mixed")
    custom = (config or {}).get("custom_instructions", "") or ""
    return _call_spec_llm(
        "technical_guidance",
        target_audience=audience,
        functional_requirements=functional_requirements_content or "N/A",
        product_context=_str_dict(product_context),
        scope=scope,
        custom_instructions=custom,
    )


def generate_data_model(
    functional_requirements_content: str, product_context: dict, config: dict
) -> str:
    """Generate Data Model Changes section."""
    audience = (config or {}).get("target_audience", "mixed")
    custom = (config or {}).get("custom_instructions", "") or ""
    return _call_spec_llm(
        "data_model_changes",
        target_audience=audience,
        functional_requirements=functional_requirements_content or "N/A",
        product_context=_str_dict(product_context),
        custom_instructions=custom,
    )


def generate_api_contracts(
    functional_requirements_content: str,
    user_stories_content: str,
    data_model_content: str,
    config: dict,
) -> str:
    """Generate API Contracts section."""
    custom = (config or {}).get("custom_instructions", "") or ""
    return _call_spec_llm(
        "api_contracts",
        target_audience=(config or {}).get("target_audience", "mixed"),
        functional_requirements=functional_requirements_content or "N/A",
        user_stories=user_stories_content or "N/A",
        data_model_changes=data_model_content or "N/A",
        custom_instructions=custom,
    )


def generate_testing_verification(
    user_stories_content: str,
    functional_requirements_content: str,
    solution_eval: dict,
    config: dict,
) -> str:
    """Generate Testing & Verification section."""
    eval_summary = json.dumps((solution_eval or {}), indent=0)[:2000]
    return _call_spec_llm(
        "testing_verification",
        target_audience=(config or {}).get("target_audience", "mixed"),
        user_stories=user_stories_content or "N/A",
        functional_requirements=functional_requirements_content or "N/A",
        solution_evaluation_summary=eval_summary,
    )
