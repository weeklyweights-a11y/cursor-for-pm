"""Tests for spec generation service (Phase 8)."""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.brief import Brief
from app.models.organization import Organization
from app.models.spec import Spec
from app.models.theme import Theme
from app.models.user import User
from app.services import spec_generation_service


def test_load_generation_context_returns_brief_and_theme_data(
    db: Session,
    test_org: Organization,
    test_theme: Theme,
    sample_brief_with_evaluation: Brief,
):
    ctx = spec_generation_service.load_generation_context(
        db, test_org.id, sample_brief_with_evaluation.id
    )
    assert ctx
    assert "brief_data" in ctx
    assert ctx["brief_data"]["theme_name"] == test_theme.name
    assert "sections" in ctx["brief_data"]
    assert "solution_evaluation" in ctx["brief_data"]
    assert "theme_data" in ctx
    assert "product_context" in ctx


def test_load_generation_context_empty_for_unknown_brief(db: Session, test_org: Organization):
    import uuid
    ctx = spec_generation_service.load_generation_context(db, test_org.id, uuid.uuid4())
    assert ctx == {}


def test_generate_all_sections_produces_sections_with_mocked_llm(
    db: Session,
    test_org: Organization,
    test_user: User,
    test_theme: Theme,
    sample_brief_with_evaluation: Brief,
):
    spec = Spec(
        org_id=test_org.id,
        brief_id=sample_brief_with_evaluation.id,
        theme_id=test_theme.id,
        created_by=test_user.id,
        version=1,
        status="generating",
        title="Test Spec",
        scope="full",
        target_audience="mixed",
        sections=[],
        is_current=True,
    )
    db.add(spec)
    db.commit()
    db.refresh(spec)

    config = {
        "scope": "full",
        "target_audience": "mixed",
        "custom_instructions": "",
    }
    with patch(
        "app.services.spec_generation_service.spec_section_generators.generate_executive_summary",
        return_value="Summary.",
    ):
        with patch(
            "app.services.spec_generation_service.spec_section_generators.generate_background_evidence",
            return_value="Evidence.",
        ):
            with patch(
                "app.services.spec_generation_service.spec_section_generators.generate_user_stories",
                return_value="US-1: Story.",
            ):
                with patch(
                    "app.services.spec_generation_service.spec_section_generators.generate_functional_requirements",
                    return_value="FR-1: Req.",
                ):
                    with patch(
                        "app.services.spec_generation_service.spec_section_generators.generate_technical_guidance",
                        return_value="Tech.",
                    ):
                        with patch(
                            "app.services.spec_generation_service.spec_section_generators.generate_data_model",
                            return_value="Tables.",
                        ):
                            with patch(
                                "app.services.spec_generation_service.spec_section_generators.generate_api_contracts",
                                return_value="API.",
                            ):
                                with patch(
                                    "app.services.spec_generation_service.spec_section_generators.generate_testing_verification",
                                    return_value="Tests.",
                                ):
                                    spec_generation_service.generate_all_sections(
                                        db,
                                        test_org.id,
                                        spec.id,
                                        sample_brief_with_evaluation.id,
                                        config,
                                    )
    db.refresh(spec)
    assert spec.status == "completed"
    assert len(spec.sections) == 8
