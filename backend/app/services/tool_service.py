"""Tool execution router for chat (Phase 6)."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.services import tool_functions


def execute_tool(
    db: Session, org_id: UUID, tool_name: str, params: dict, user_id: UUID | None = None
) -> dict:
    """Route to the correct tool function. Returns result dict. user_id required for generate_brief and generate_spec."""
    params = params or {}
    handlers = {
        "search_feedback": tool_functions.search_feedback_tool,
        "get_theme": tool_functions.get_theme_tool,
        "list_themes": tool_functions.list_themes_tool,
        "compare_segments": tool_functions.compare_segments_tool,
        "get_customer_feedback": tool_functions.get_customer_feedback_tool,
        "get_stats": tool_functions.get_stats_tool,
        "filter_feedback": tool_functions.filter_feedback_tool,
        "generate_brief": lambda d, o, p: tool_functions.generate_brief_tool(d, o, p, user_id),
        "generate_spec": lambda d, o, p: tool_functions.generate_spec_tool(d, o, p, user_id),
        "get_spec_section": tool_functions.get_spec_section_tool,
    }
    fn = handlers.get(tool_name)
    if not fn:
        return {"error": f"Unknown tool: {tool_name}."}
    try:
        return fn(db, org_id, params)
    except Exception as e:
        return {"error": str(e)}
