"""Tests for spec service (Phase 8)."""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.brief import Brief
from app.models.organization import Organization
from app.models.spec import Spec
from app.models.theme import Theme
from app.models.user import User
from app.services import spec_service


def test_generate_spec_requires_solution_evaluation(
    db: Session, test_org: Organization, test_user: User, sample_brief: Brief
):
    """generate_spec returns None when brief has no solution_evaluation."""
    assert sample_brief.solution_evaluation is None
    spec_id = spec_service.generate_spec(
        db, test_org.id, sample_brief.id, test_user.id, "full", "mixed", None
    )
    assert spec_id is None


def test_generate_spec_creates_record_and_queues_task(
    db: Session,
    test_org: Organization,
    test_user: User,
    sample_brief_with_evaluation: Brief,
):
    with patch("app.tasks.spec_tasks.generate_spec_task") as mock_task:
        mock_task.delay.return_value = None
        spec_id = spec_service.generate_spec(
            db,
            test_org.id,
            sample_brief_with_evaluation.id,
            test_user.id,
            "full",
            "mixed",
            None,
        )
    assert spec_id is not None
    spec = spec_service.get_spec(db, test_org.id, spec_id)
    assert spec is not None
    assert spec.status == "generating"
    assert spec.brief_id == sample_brief_with_evaluation.id
    assert spec.version == 1
    mock_task.delay.assert_called_once()


def test_get_spec_returns_sections_when_completed(
    db: Session, test_org: Organization, sample_spec: Spec
):
    s = spec_service.get_spec(db, test_org.id, sample_spec.id)
    assert s is not None
    assert len(s.sections) >= 1
    assert s.status == "completed"


def test_get_current_spec_returns_latest(
    db: Session,
    test_org: Organization,
    sample_brief_with_evaluation: Brief,
    sample_spec: Spec,
):
    current = spec_service.get_current_spec(
        db, test_org.id, sample_brief_with_evaluation.id
    )
    assert current is not None
    assert current.id == sample_spec.id


def test_new_spec_for_same_brief_increments_version(
    db: Session,
    test_org: Organization,
    test_user: User,
    sample_brief_with_evaluation: Brief,
    sample_spec: Spec,
):
    with patch("app.tasks.spec_tasks.generate_spec_task") as mock_task:
        mock_task.delay.return_value = None
        new_id = spec_service.generate_spec(
            db,
            test_org.id,
            sample_brief_with_evaluation.id,
            test_user.id,
            "mvp",
            "ai_agent",
            None,
        )
    assert new_id != sample_spec.id
    db.refresh(sample_spec)
    assert sample_spec.is_current is False
    new_spec = spec_service.get_spec(db, test_org.id, new_id)
    assert new_spec.version == 2
    assert new_spec.is_current is True


def test_spec_filters_by_org_id(
    db: Session,
    test_org: Organization,
    second_org: Organization,
    sample_spec: Spec,
):
    other = spec_service.get_spec(db, second_org.id, sample_spec.id)
    assert other is None


def test_export_spec_markdown_returns_content(
    db: Session, test_org: Organization, sample_spec: Spec
):
    result = spec_service.export_spec_markdown(db, test_org.id, sample_spec.id)
    assert result is not None
    content, filename = result
    assert "Implementation Spec" in content or "Executive Summary" in content
    assert filename.endswith(".md")


def test_export_spec_cursor_format_returns_content(
    db: Session, test_org: Organization, sample_spec: Spec
):
    result = spec_service.export_spec_cursor_format(db, test_org.id, sample_spec.id)
    assert result is not None
    content, filename = result
    assert len(content) > 0
    assert "cursor" in filename or ".md" in filename


def test_get_spec_other_org_returns_none(
    db: Session, second_org: Organization, sample_spec: Spec
):
    s = spec_service.get_spec(db, second_org.id, sample_spec.id)
    assert s is None
