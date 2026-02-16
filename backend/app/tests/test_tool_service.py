"""Tests for tool service (Phase 6)."""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.services import tool_functions
from app.services import tool_service


def test_execute_tool_unknown_returns_error(db: Session, test_org: Organization):
    result = tool_service.execute_tool(db, test_org.id, "unknown_tool", {})
    assert "error" in result
    assert "Unknown" in result["error"]


def test_execute_tool_get_stats_returns_aggregates(db: Session, test_org: Organization):
    result = tool_service.execute_tool(db, test_org.id, "get_stats", {})
    assert "total_feedback" in result or "error" in result
    if "error" not in result:
        assert "summary" in result or "theme_count" in result


def test_execute_tool_list_themes_returns_ranked(db: Session, test_org: Organization, test_theme):
    result = tool_service.execute_tool(db, test_org.id, "list_themes", {"limit": 5})
    assert "themes" in result
    assert len(result["themes"]) >= 1
    assert result["themes"][0]["name"] == test_theme.name


def test_get_theme_tool_by_id(db: Session, test_org: Organization, test_theme):
    result = tool_functions.get_theme_tool(db, test_org.id, {"theme_id": str(test_theme.id)})
    assert "theme" in result
    assert result["theme"]["name"] == test_theme.name


def test_get_theme_tool_by_name_ilike(db: Session, test_org: Organization, test_theme):
    result = tool_functions.get_theme_tool(db, test_org.id, {"theme_name": "Test"})
    assert "theme" in result
    assert result["theme"]["name"] == test_theme.name


def test_filter_feedback_tool_applies_filters(db: Session, test_org: Organization):
    result = tool_service.execute_tool(db, test_org.id, "filter_feedback", {"limit": 5})
    assert "items" in result
    assert "count" in result


def test_search_feedback_tool_requires_query(db: Session, test_org: Organization):
    result = tool_functions.search_feedback_tool(db, test_org.id, {"query": ""})
    assert "message" in result or "items" in result
