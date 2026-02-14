"""Tests for product context service. Create, get, update, has; duplicate error; org isolation."""

import pytest
from sqlalchemy.orm import Session

from app.exceptions import AlreadyExistsError, NotFoundError
from app.models.organization import Organization
from app.schemas.product_context import ProductContextCreateRequest, ProductContextUpdateRequest
from app.services import product_context_service


def test_create_product_context(db: Session, test_org: Organization):
    data = ProductContextCreateRequest(
        product_name="My Product",
        product_description="Does things",
        existing_features=["Search", "Export"],
        target_users="PMs",
        known_limitations=["No mobile"],
        additional_context=None,
    )
    ctx = product_context_service.create_product_context(db, test_org.id, data)
    assert ctx.id is not None
    assert ctx.org_id == test_org.id
    assert ctx.product_name == "My Product"
    assert ctx.existing_features == ["Search", "Export"]
    assert ctx.known_limitations == ["No mobile"]


def test_create_product_context_duplicate_raises(db: Session, test_org: Organization):
    data = ProductContextCreateRequest(
        product_name="X",
        product_description="Y",
    )
    product_context_service.create_product_context(db, test_org.id, data)
    with pytest.raises(AlreadyExistsError):
        product_context_service.create_product_context(db, test_org.id, data)


def test_get_product_context(db: Session, test_org: Organization):
    data = ProductContextCreateRequest(product_name="P", product_description="D")
    created = product_context_service.create_product_context(db, test_org.id, data)
    got = product_context_service.get_product_context(db, test_org.id)
    assert got.id == created.id
    assert got.product_name == "P"


def test_get_product_context_not_found_raises(db: Session, test_org: Organization):
    with pytest.raises(NotFoundError):
        product_context_service.get_product_context(db, test_org.id)


def test_has_product_context(db: Session, test_org: Organization):
    assert product_context_service.has_product_context(db, test_org.id) is False
    data = ProductContextCreateRequest(product_name="P", product_description="D")
    product_context_service.create_product_context(db, test_org.id, data)
    assert product_context_service.has_product_context(db, test_org.id) is True


def test_update_product_context(db: Session, test_org: Organization):
    data = ProductContextCreateRequest(product_name="P", product_description="D")
    product_context_service.create_product_context(db, test_org.id, data)
    update = ProductContextUpdateRequest(product_name="P2", product_description="D2")
    updated = product_context_service.update_product_context(db, test_org.id, update)
    assert updated.product_name == "P2"
    assert updated.product_description == "D2"


def test_update_product_context_not_found_raises(db: Session, test_org: Organization):
    update = ProductContextUpdateRequest(product_name="P2")
    with pytest.raises(NotFoundError):
        product_context_service.update_product_context(db, test_org.id, update)


def test_product_context_org_isolation(db: Session, test_org: Organization, second_org: Organization):
    data = ProductContextCreateRequest(product_name="P", product_description="D")
    product_context_service.create_product_context(db, test_org.id, data)
    assert product_context_service.has_product_context(db, test_org.id) is True
    assert product_context_service.has_product_context(db, second_org.id) is False
    with pytest.raises(NotFoundError):
        product_context_service.get_product_context(db, second_org.id)
