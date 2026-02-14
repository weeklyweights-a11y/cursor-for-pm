import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.services import batch_service


def test_create_batch(db: Session, test_org: Organization):
    batch = batch_service.create_batch(
        db, test_org.id, "test.csv", total_rows=10, column_mapping={"content": 0}
    )
    assert batch.id is not None
    assert batch.org_id == test_org.id
    assert batch.filename == "test.csv"
    assert batch.total_rows == 10
    assert batch.status == "pending"
    assert batch.processed_rows == 0


def test_update_batch_progress(db: Session, test_org: Organization):
    batch = batch_service.create_batch(db, test_org.id, "test.csv", 100)
    updated = batch_service.update_batch_progress(db, batch.id, 50, 48, 2)
    assert updated is not None
    assert updated.processed_rows == 50
    assert updated.successful_rows == 48
    assert updated.failed_rows == 2
    assert updated.status == "processing"


def test_complete_batch(db: Session, test_org: Organization):
    batch = batch_service.create_batch(db, test_org.id, "test.csv", 5)
    completed = batch_service.complete_batch(db, batch.id)
    assert completed is not None
    assert completed.status == "completed"


def test_fail_batch(db: Session, test_org: Organization):
    batch = batch_service.create_batch(db, test_org.id, "test.csv", 5)
    failed = batch_service.fail_batch(db, batch.id, "File not found")
    assert failed is not None
    assert failed.status == "failed"
    assert failed.error_message == "File not found"


def test_get_batch(db: Session, test_org: Organization):
    batch = batch_service.create_batch(db, test_org.id, "test.csv", 3)
    got = batch_service.get_batch(db, test_org.id, batch.id)
    assert got is not None
    assert got.id == batch.id


def test_get_batch_wrong_org_returns_none(db: Session, test_org: Organization, second_org: Organization):
    batch = batch_service.create_batch(db, test_org.id, "test.csv", 3)
    got = batch_service.get_batch(db, second_org.id, batch.id)
    assert got is None


def test_get_batches_paginated(db: Session, test_org: Organization):
    for i in range(5):
        batch_service.create_batch(db, test_org.id, f"f{i}.csv", 1)
    items, total = batch_service.get_batches(db, test_org.id, page=1, page_size=2)
    assert len(items) == 2
    assert total == 5
