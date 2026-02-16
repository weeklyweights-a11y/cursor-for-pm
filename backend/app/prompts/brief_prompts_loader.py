"""Load brief section and solution-evaluation prompt templates from .txt files (Phase 7)."""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent

SECTION_KEYS = [
    "problem_statement",
    "customer_impact",
    "evidence_summary",
    "trend_analysis",
    "business_case",
    "recommended_action",
    "risks",
]


def _load_template(name: str) -> str:
    path = _PROMPTS_DIR / f"brief_{name}.txt"
    return path.read_text(encoding="utf-8").strip()


def get_section_templates() -> dict[str, str]:
    """Return dict of section_key -> template string (with {placeholders})."""
    return {key: _load_template(key) for key in SECTION_KEYS}


def get_solution_evaluation_template() -> str:
    """Return the solution evaluation prompt template."""
    return _load_template("solution_evaluation")
