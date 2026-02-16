"""Tests for brief generation service (Phase 7)."""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.theme import Theme
from app.services import brief_generation_service


def test_load_theme_context_returns_theme_and_feedback(
    db: Session, test_org: Organization, test_theme: Theme
):
    ctx = brief_generation_service.load_theme_context(db, test_org.id, test_theme.id)
    assert ctx
    assert "theme_data" in ctx
    assert ctx["theme_data"]["name"] == test_theme.name
    assert "feedback_items" in ctx
    assert "customers" in ctx


def test_load_theme_context_empty_for_unknown_theme(db: Session, test_org: Organization):
    import uuid
    ctx = brief_generation_service.load_theme_context(db, test_org.id, uuid.uuid4())
    assert ctx == {}


def test_generate_all_sections_produces_sections_with_mocked_llm(
    db: Session, test_org: Organization, test_user, test_theme: Theme
):
    from app.models.brief import Brief
    brief = Brief(
        org_id=test_org.id,
        theme_id=test_theme.id,
        created_by=test_user.id if hasattr(test_user, "id") else test_user,
        version=1,
        status="generating",
        title="Test Brief",
        sections=[],
        is_current=True,
    )
    db.add(brief)
    db.commit()
    db.refresh(brief)

    with patch("app.services.brief_generation_service.brief_section_generators.generate_problem_statement", return_value="Problem."):
        with patch("app.services.brief_generation_service.brief_section_generators.generate_customer_impact", return_value="Impact."):
            with patch("app.services.brief_generation_service.brief_section_generators.generate_evidence_summary", return_value="Evidence."):
                with patch("app.services.brief_generation_service.brief_section_generators.generate_trend_analysis", return_value="Trend."):
                    with patch("app.services.brief_generation_service.brief_section_generators.generate_business_case", return_value="Business."):
                        with patch("app.services.brief_generation_service.brief_section_generators.generate_recommended_action", return_value="Action."):
                            with patch("app.services.brief_generation_service.brief_section_generators.generate_risks", return_value="Risks."):
                                brief_generation_service.generate_all_sections(
                                    db, test_org.id, brief.id, test_theme.id
                                )
    db.refresh(brief)
    assert brief.status == "completed"
    assert len(brief.sections) == 7


def test_solution_evaluation_returns_valid_structure():
    from app.services import brief_section_generators
    theme_data = {"name": "Test", "description": ""}
    feedback_items = [{"pain_point": "P1", "feature_gap": "F1"}]
    with patch("app.services.brief_section_generators.llm_chat.call_brief_llm") as mock_llm:
        mock_llm.return_value = (
            '{"pain_points_addressed": [{"pain_point": "P1", "addressed": true, "explanation": "Yes"}], '
            '"coverage_score": 0.8, "segment_impact": {}, "strengths": [], "gaps": [], '
            '"recommended_additions": [], "predicted_impact_score": 0.75}'
        )
        out = brief_section_generators.evaluate_solution_against_evidence(
            theme_data, feedback_items, "We will fix P1."
        )
    assert "coverage_score" in out
    assert 0.0 <= out["coverage_score"] <= 1.0
    assert "pain_points_addressed" in out
