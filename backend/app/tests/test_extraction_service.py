"""Tests for extraction service. Mocks LLM; temperature=0 and prompt fallback (GAP 2/3)."""

from uuid import uuid4
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy.orm import Session

from app.models.feedback_item import FeedbackItem
from app.models.organization import Organization
from app.models.product_context import ProductContext
from app.services import extraction_service


def _valid_result():
    return {
        "pain_point": "Slow search",
        "topic": "search",
        "related_feature": "Search",
        "is_existing_feature": True,
        "feature_gap": "Performance",
        "urgency": "high",
        "sentiment": "negative",
        "verbatim_quote": "Search is too slow",
        "confidence": 0.9,
    }


def test_build_extraction_prompt_fallback_when_no_context():
    prompt = extraction_service.build_extraction_prompt("Feedback text", None)
    assert "No product context provided. Extract signals based on the feedback text alone." in prompt
    assert "Feedback text" in prompt


def test_build_extraction_prompt_includes_context_when_present():
    ctx = MagicMock()
    ctx.product_name = "MyApp"
    ctx.product_description = "Does things"
    ctx.existing_features = ["Search"]
    ctx.known_limitations = ["No mobile"]
    ctx.target_users = "PMs"
    ctx.additional_context = None
    prompt = extraction_service.build_extraction_prompt("Feedback text", ctx)
    assert "MyApp" in prompt
    assert "Does things" in prompt
    assert "Search" in prompt
    assert "No mobile" in prompt
    assert "PMs" in prompt
    assert "Feedback text" in prompt


def test_validate_extraction_result_valid():
    assert extraction_service.validate_extraction_result(_valid_result()) is True


def test_validate_extraction_result_invalid_urgency():
    r = _valid_result()
    r["urgency"] = "invalid"
    assert extraction_service.validate_extraction_result(r) is False


def test_validate_extraction_result_invalid_sentiment():
    r = _valid_result()
    r["sentiment"] = "angry"
    assert extraction_service.validate_extraction_result(r) is False


def test_validate_extraction_result_missing_pain_point():
    r = _valid_result()
    r["pain_point"] = ""
    assert extraction_service.validate_extraction_result(r) is False


def test_validate_extraction_result_confidence_out_of_range():
    r = _valid_result()
    r["confidence"] = 1.5
    assert extraction_service.validate_extraction_result(r) is False


def test_extract_signals_completes_and_saves(db: Session, test_org: Organization):
    item = FeedbackItem(
        org_id=test_org.id,
        content="Search is slow",
        source_type="manual",
        source_id="manual:test-1",
        extraction_status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    with patch.object(extraction_service, "call_llm", return_value=(_valid_result(), "{}")) as m:
        extraction_service.extract_signals(db, item.id, test_org.id)
    m.assert_called_once()
    call_kwargs = m.call_args[1]
    assert call_kwargs.get("temperature") == 0  # GAP 2
    db.refresh(item)
    assert item.extraction_status == "completed"
    assert item.pain_point == "Slow search"
    assert item.topic == "search"
    assert item.urgency == "high"
    assert item.extraction_confidence == 0.9


def test_extract_signals_skips_when_already_completed(db: Session, test_org: Organization):
    item = FeedbackItem(
        org_id=test_org.id,
        content="Already done",
        source_type="manual",
        source_id="manual:test-2",
        extraction_status="completed",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    with patch.object(extraction_service, "call_llm") as mock_llm:
        extraction_service.extract_signals(db, item.id, test_org.id)
    mock_llm.assert_not_called()


def test_extract_signals_invalid_result_sets_failed(db: Session, test_org: Organization):
    item = FeedbackItem(
        org_id=test_org.id,
        content="Some feedback",
        source_type="manual",
        source_id="manual:test-3",
        extraction_status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    invalid = _valid_result()
    invalid["urgency"] = "invalid"
    with patch.object(extraction_service, "call_llm", return_value=(invalid, "{}")):
        extraction_service.extract_signals(db, item.id, test_org.id)
    db.refresh(item)
    assert item.extraction_status == "failed"
    assert item.raw_llm_response is not None


def test_get_extraction_stats(db: Session, test_org: Organization):
    for i in range(2):
        item = FeedbackItem(
            org_id=test_org.id,
            content=f"Feedback {i}",
            source_type="manual",
            source_id=f"manual:stats-{i}",
            extraction_status="pending",
        )
        db.add(item)
    item2 = FeedbackItem(
        org_id=test_org.id,
        content="Done",
        source_type="manual",
        source_id="manual:stats-done",
        extraction_status="completed",
    )
    db.add(item2)
    db.commit()
    stats = extraction_service.get_extraction_stats(db, test_org.id)
    assert stats["total"] == 3
    assert stats["pending"] == 2
    assert stats["completed"] == 1
    assert stats["failed"] == 0
