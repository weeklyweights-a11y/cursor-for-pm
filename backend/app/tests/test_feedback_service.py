import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.organization import Organization
from app.services import feedback_service


def test_create_feedback_item(db: Session, test_org: Organization):
    item = feedback_service.create_feedback_item(
        db,
        test_org.id,
        content="Great feature",
        source_type="manual",
        source_id="manual:abc",
    )
    assert item.id is not None
    assert item.content == "Great feature"
    assert item.source_type == "manual"
    assert item.source_id == "manual:abc"
    assert item.org_id == test_org.id


def test_check_duplicate(db: Session, test_org: Organization):
    feedback_service.create_feedback_item(
        db, test_org.id, "x", "manual", "manual:1"
    )
    assert feedback_service.check_duplicate(db, test_org.id, "manual:1") is True
    assert feedback_service.check_duplicate(db, test_org.id, "manual:2") is False


def test_create_feedback_items_batch_idempotent(db: Session, test_org: Organization):
    """GAP 5: running twice does not create duplicates."""
    batch_id = uuid.uuid4()
    batch = Batch(
        id=batch_id,
        org_id=test_org.id,
        filename="test.csv",
        total_rows=2,
        status="processing",
    )
    db.add(batch)
    db.commit()
    items = [{"content": "Row 0", "author_name": "A"}, {"content": "Row 1"}]
    created_ids1, skip1 = feedback_service.create_feedback_items_batch(
        db, test_org.id, batch_id, items, source_id_prefix=str(batch_id), start_row=0
    )
    assert len(created_ids1) == 2
    assert skip1 == 0
    created_ids2, skip2 = feedback_service.create_feedback_items_batch(
        db, test_org.id, batch_id, items, source_id_prefix=str(batch_id), start_row=0
    )
    assert len(created_ids2) == 0
    assert skip2 == 2


def test_get_feedback_items_paginated(db: Session, test_org: Organization):
    for i in range(3):
        feedback_service.create_feedback_item(
            db, test_org.id, f"Content {i}", "manual", f"manual:{i}"
        )
    items, total = feedback_service.get_feedback_items(db, test_org.id, page=1, page_size=2)
    assert len(items) == 2
    assert total == 3


def test_get_feedback_items_filter_source_type(db: Session, test_org: Organization):
    feedback_service.create_feedback_item(db, test_org.id, "a", "manual", "m:1")
    feedback_service.create_feedback_item(db, test_org.id, "b", "slack", "s:1")
    items, total = feedback_service.get_feedback_items(db, test_org.id, source_type_filter="manual")
    assert len(items) == 1
    assert total == 1
    assert items[0].source_type == "manual"


def test_get_feedback_item_org_isolation(db: Session, test_org: Organization, second_org: Organization):
    item = feedback_service.create_feedback_item(db, test_org.id, "x", "manual", "m:1")
    got = feedback_service.get_feedback_item(db, second_org.id, item.id)
    assert got is None
