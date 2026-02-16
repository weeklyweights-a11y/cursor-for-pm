"""Tests for brief service (Phase 7)."""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.brief import Brief
from app.models.organization import Organization
from app.models.theme import Theme
from app.models.user import User
from app.services import brief_service


def test_generate_brief_creates_record_and_queues_task(
    db: Session, test_org: Organization, test_user: User, test_theme: Theme
):
    with patch("app.tasks.brief_tasks.generate_brief_task") as mock_task:
        mock_task.delay.return_value = None
        brief_id = brief_service.generate_brief(db, test_org.id, test_theme.id, test_user.id)
    assert brief_id is not None
    brief = brief_service.get_brief(db, test_org.id, brief_id)
    assert brief is not None
    assert brief.status == "generating"
    assert brief.theme_id == test_theme.id
    assert brief.version == 1
    mock_task.delay.assert_called_once()


def test_get_brief_returns_sections_when_completed(db: Session, test_org: Organization, sample_brief: Brief):
    b = brief_service.get_brief(db, test_org.id, sample_brief.id)
    assert b is not None
    assert len(b.sections) >= 1
    assert b.status == "completed"


def test_get_current_brief_returns_latest(db: Session, test_org: Organization, test_theme: Theme, sample_brief: Brief):
    current = brief_service.get_current_brief(db, test_org.id, test_theme.id)
    assert current is not None
    assert current.id == sample_brief.id


def test_generate_new_brief_increments_version_and_sets_previous_not_current(
    db: Session, test_org: Organization, test_user: User, test_theme: Theme, sample_brief: Brief
):
    with patch("app.tasks.brief_tasks.generate_brief_task") as mock_task:
        mock_task.delay.return_value = None
        new_id = brief_service.generate_brief(db, test_org.id, test_theme.id, test_user.id)
    assert new_id != sample_brief.id
    db.refresh(sample_brief)
    assert sample_brief.is_current is False
    new_brief = brief_service.get_brief(db, test_org.id, new_id)
    assert new_brief.version == 2
    assert new_brief.is_current is True


def test_brief_filters_by_org_id(db: Session, test_org: Organization, second_org: Organization, sample_brief: Brief):
    other = brief_service.get_brief(db, second_org.id, sample_brief.id)
    assert other is None


def test_get_brief_other_org_returns_none(db: Session, second_org: Organization, sample_brief: Brief):
    b = brief_service.get_brief(db, second_org.id, sample_brief.id)
    assert b is None
