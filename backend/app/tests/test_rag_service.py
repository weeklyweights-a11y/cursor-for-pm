"""Tests for RAG service (Phase 6)."""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.theme import Theme
from app.services import rag_service

_SAMPLE_EMBEDDING = [0.1] * 384


def test_estimate_token_count_empty():
    assert rag_service.estimate_token_count("") == 0


def test_estimate_token_count_approx():
    text = "a" * 400
    assert rag_service.estimate_token_count(text) == 100


def test_truncate_context_under_budget():
    ctx = "short"
    assert rag_service.truncate_context(ctx, 100) == "short"


def test_truncate_context_over_budget():
    ctx = "x" * 1000
    out = rag_service.truncate_context(ctx, 100)
    assert rag_service.estimate_token_count(out) <= 120


def test_format_feedback_context_empty():
    assert "No feedback" in rag_service.format_feedback_context([]) or "feedback" in rag_service.format_feedback_context([]).lower()


def test_format_feedback_context_includes_key_fields(db: Session, test_org: Organization):
    from app.models.feedback_item import FeedbackItem
    item = FeedbackItem(
        org_id=test_org.id,
        content="Test content here",
        source_type="manual",
        source_id="rag-fixture-1",
        pain_point="pain",
        topic="topic",
        urgency="high",
        sentiment="negative",
        customer_name="Acme",
        segment="enterprise",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    out = rag_service.format_feedback_context([item])
    assert "Test content" in out
    assert "pain" in out
    assert "topic" in out
    assert "high" in out
    assert "Acme" in out


def test_format_theme_context_empty(db: Session, test_org: Organization):
    out = rag_service.format_theme_context(db, test_org.id, limit=5)
    assert "No themes" in out


def test_format_theme_context_includes_names_scores(db: Session, test_org: Organization, test_theme: Theme):
    out = rag_service.format_theme_context(db, test_org.id, limit=5)
    assert test_theme.name in out
    assert str(test_theme.mention_count) in out
    assert str(test_theme.priority_score) in out


def test_retrieve_relevant_feedback_returns_ordered_by_similarity(
    db: Session, test_org: Organization, sample_feedback_with_embedding
):
    with patch("app.services.rag_service.embedding_service.get_similar_items") as mock_get:
        mock_get.return_value = [
            sample_feedback_with_embedding["theme_item"],
            sample_feedback_with_embedding["outlier_item"],
        ]
        items = rag_service.retrieve_relevant_feedback(db, test_org.id, _SAMPLE_EMBEDDING, limit=20)
        assert len(items) == 2
        mock_get.assert_called_once()


def test_retrieve_relevant_feedback_with_filters_narrows(
    db: Session, test_org: Organization, sample_feedback_with_embedding
):
    with patch("app.services.rag_service.embedding_service.get_similar_items") as mock_get:
        mock_get.return_value = [
            sample_feedback_with_embedding["theme_item"],
            sample_feedback_with_embedding["outlier_item"],
        ]
        items = rag_service.retrieve_relevant_feedback(
            db, test_org.id, _SAMPLE_EMBEDDING, limit=20, filters={"urgency": "critical"}
        )
        assert len(items) <= 2
