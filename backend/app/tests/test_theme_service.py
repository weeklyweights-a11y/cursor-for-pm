"""Tests for theme service."""

import pytest
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.theme import Theme
from app.services import theme_service


def test_get_themes_empty(db: Session, test_org: Organization):
    themes, total = theme_service.get_themes(db, test_org.id, page=1, page_size=20)
    assert themes == []
    assert total == 0


def test_get_themes_returns_paginated(db: Session, test_org: Organization, test_theme: Theme):
    themes, total = theme_service.get_themes(db, test_org.id, page=1, page_size=20)
    assert total == 1
    assert len(themes) == 1
    assert themes[0].name == "Test Theme"


def test_get_theme(db: Session, test_org: Organization, test_theme: Theme):
    t = theme_service.get_theme(db, test_org.id, test_theme.id)
    assert t is not None
    assert t.id == test_theme.id
    assert t.name == "Test Theme"


def test_get_theme_other_org_returns_none(db: Session, test_theme: Theme, second_org: Organization):
    t = theme_service.get_theme(db, second_org.id, test_theme.id)
    assert t is None


def test_get_outliers_empty(db: Session, test_org: Organization):
    items, total = theme_service.get_outliers(db, test_org.id)
    assert items == []
    assert total == 0
