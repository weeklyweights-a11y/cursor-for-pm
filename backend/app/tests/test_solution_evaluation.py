"""Tests for solution evaluation (Phase 7)."""

from unittest.mock import patch

import pytest

from app.services import brief_section_generators


def test_solution_addressing_all_pain_points_gets_high_coverage():
    with patch("app.services.brief_section_generators.llm_chat.call_brief_llm") as mock_llm:
        mock_llm.return_value = (
            '{"pain_points_addressed": ['
            '{"pain_point": "P1", "addressed": true, "explanation": "Yes"},'
            '{"pain_point": "P2", "addressed": true, "explanation": "Yes"}], '
            '"coverage_score": 1.0, "segment_impact": {}, "strengths": ["All addressed"], '
            '"gaps": [], "recommended_additions": [], "predicted_impact_score": 0.9}'
        )
        out = brief_section_generators.evaluate_solution_against_evidence(
            {"name": "T"}, [{"pain_point": "P1"}, {"pain_point": "P2"}], "Full solution."
        )
    assert out["coverage_score"] == 1.0
    assert len(out["pain_points_addressed"]) == 2
    assert all(p["addressed"] for p in out["pain_points_addressed"])


def test_solution_addressing_none_gets_low_coverage():
    with patch("app.services.brief_section_generators.llm_chat.call_brief_llm") as mock_llm:
        mock_llm.return_value = (
            '{"pain_points_addressed": ['
            '{"pain_point": "P1", "addressed": false, "explanation": "No"}], '
            '"coverage_score": 0.0, "segment_impact": {}, "strengths": [], '
            '"gaps": ["Misses P1"], "recommended_additions": ["Add P1"], '
            '"predicted_impact_score": 0.2}'
        )
        out = brief_section_generators.evaluate_solution_against_evidence(
            {"name": "T"}, [{"pain_point": "P1"}], "Unrelated solution."
        )
    assert out["coverage_score"] == 0.0
    assert out["pain_points_addressed"][0]["addressed"] is False
    assert "Misses P1" in out.get("gaps", [])


def test_partial_solution_gets_proportional_score():
    with patch("app.services.brief_section_generators.llm_chat.call_brief_llm") as mock_llm:
        mock_llm.return_value = (
            '{"pain_points_addressed": ['
            '{"pain_point": "P1", "addressed": true}, {"pain_point": "P2", "addressed": false}], '
            '"coverage_score": 0.5, "segment_impact": {}, "strengths": [], "gaps": [], '
            '"recommended_additions": [], "predicted_impact_score": 0.5}'
        )
        out = brief_section_generators.evaluate_solution_against_evidence(
            {"name": "T"}, [{"pain_point": "P1"}, {"pain_point": "P2"}], "Half solution."
        )
    assert out["coverage_score"] == 0.5
    assert len(out["pain_points_addressed"]) == 2


def test_evaluation_includes_gaps_and_recommendations():
    with patch("app.services.brief_section_generators.llm_chat.call_brief_llm") as mock_llm:
        mock_llm.return_value = (
            '{"pain_points_addressed": [{"pain_point": "No SSO", "addressed": false}], '
            '"coverage_score": 0.3, "segment_impact": {}, '
            '"strengths": ["Good start"], "gaps": ["No SCIM"], '
            '"recommended_additions": ["Add SCIM"], "predicted_impact_score": 0.4}'
        )
        out = brief_section_generators.evaluate_solution_against_evidence(
            {"name": "SSO"}, [{"pain_point": "No SSO"}], "Partial SSO."
        )
    assert "No SCIM" in out.get("gaps", [])
    assert "Add SCIM" in out.get("recommended_additions", [])
