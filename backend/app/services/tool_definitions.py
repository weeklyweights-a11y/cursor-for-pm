"""Tool schemas for chat LLM (Phase 6)."""


def get_tool_definitions() -> list[dict]:
    """Return list of 7 tool schemas for the LLM (Anthropic format)."""
    return [
        {
            "name": "search_feedback",
            "description": "Search feedback by text similarity. Returns matching feedback items with content, pain_point, topic, urgency, sentiment, customer, segment, theme.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max items", "default": 10},
                    "segment": {"type": "string", "description": "Filter by segment"},
                    "urgency": {"type": "string", "description": "Filter by urgency"},
                    "source_type": {"type": "string", "description": "Filter by source: csv, manual, slack"},
                },
            },
        },
        {
            "name": "get_theme",
            "description": "Get a specific theme's details: name, mention_count, priority_score, score_breakdown, top_quotes.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "theme_name": {"type": "string", "description": "Theme name (fuzzy match)"},
                    "theme_id": {"type": "string", "description": "Theme UUID"},
                },
            },
        },
        {
            "name": "list_themes",
            "description": "Get all current themes ranked by priority or mention count.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "sort_by": {"type": "string", "description": "priority_score, mention_count, or urgency", "default": "priority_score"},
                    "limit": {"type": "integer", "description": "Max themes", "default": 10},
                },
            },
        },
        {
            "name": "compare_segments",
            "description": "Compare feedback across customer segments. Returns per-segment: count, top themes, urgency breakdown, sentiment breakdown.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "segments": {"type": "array", "items": {"type": "string"}, "description": "e.g. [\"enterprise\", \"smb\"]"},
                    "topic": {"type": "string", "description": "Optional topic filter"},
                },
            },
        },
        {
            "name": "get_customer_feedback",
            "description": "Get feedback for a specific customer by name or ID.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Company or customer name"},
                    "customer_id": {"type": "string", "description": "Customer UUID"},
                    "limit": {"type": "integer", "description": "Max items", "default": 10},
                },
            },
        },
        {
            "name": "get_stats",
            "description": "Get overall dashboard statistics: total feedback, by source, by status, theme count, top customers, extraction/enrichment stats.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "filter_feedback",
            "description": "Filter feedback by multiple criteria.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "segment": {"type": "string"},
                    "urgency": {"type": "string"},
                    "sentiment": {"type": "string"},
                    "theme": {"type": "string"},
                    "source_type": {"type": "string"},
                    "date_from": {"type": "string", "description": "ISO date"},
                    "date_to": {"type": "string", "description": "ISO date"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        },
        {
            "name": "generate_brief",
            "description": "Generate an evidence brief for a theme by name or id. Returns link to the brief.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "theme_name": {"type": "string", "description": "Theme name (fuzzy match)"},
                    "theme_id": {"type": "string", "description": "Theme UUID"},
                },
            },
        },
        {
            "name": "generate_spec",
            "description": "Generate an implementation spec for a theme or brief. The brief must have a solution evaluation. Returns link to the spec. Use theme_name, theme_id, or brief_id.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "theme_name": {"type": "string", "description": "Theme name (fuzzy match)"},
                    "theme_id": {"type": "string", "description": "Theme UUID"},
                    "brief_id": {"type": "string", "description": "Brief UUID (must have solution evaluation)"},
                    "scope": {"type": "string", "description": "mvp or full", "default": "full"},
                    "target_audience": {"type": "string", "description": "ai_agent, engineer, or mixed", "default": "mixed"},
                },
            },
        },
        {
            "name": "get_spec_section",
            "description": "Get a section of an implementation spec (e.g. user_stories, executive_summary). Provide theme_name, theme_id, or spec_id, and section_key.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "theme_name": {"type": "string", "description": "Theme name (fuzzy match)"},
                    "theme_id": {"type": "string", "description": "Theme UUID"},
                    "spec_id": {"type": "string", "description": "Spec UUID"},
                    "section_key": {"type": "string", "description": "e.g. user_stories, executive_summary, functional_requirements", "default": "user_stories"},
                },
            },
        },
    ]


def get_ollama_tool_prompt() -> str:
    """Format tool descriptions for Ollama system prompt injection."""
    tools = get_tool_definitions()
    lines = ["Available tools (respond with JSON to call): {\"tool\": \"name\", \"params\": {...}}"]
    for t in tools:
        lines.append(f"- {t['name']}: {t['description']}")
    return "\n".join(lines)
