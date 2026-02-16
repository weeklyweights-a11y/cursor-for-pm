"""Load spec section prompt templates from .txt files (Phase 8)."""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent

SECTION_KEYS = [
    "executive_summary",
    "background_evidence",
    "user_stories",
    "functional_requirements",
    "technical_guidance",
    "data_model_changes",
    "api_contracts",
    "testing_verification",
]


def _load_template(name: str) -> str:
    path = _PROMPTS_DIR / f"spec_{name}.txt"
    return path.read_text(encoding="utf-8").strip()


def get_section_template(section_key: str) -> str:
    """Return template string for section_key (with {placeholders})."""
    if section_key not in SECTION_KEYS:
        raise ValueError(f"Unknown section_key: {section_key}")
    return _load_template(section_key)


def get_section_templates() -> dict[str, str]:
    """Return dict of section_key -> template string."""
    return {key: _load_template(key) for key in SECTION_KEYS}


def get_cursor_export_template() -> str:
    """Return template for Cursor-optimized export (goal, done-means, evidence, tables, criteria, trail)."""
    path = _PROMPTS_DIR / "spec_export.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""
