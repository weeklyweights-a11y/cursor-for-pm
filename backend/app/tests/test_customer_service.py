"""Tests for customer_service: normalize, upload, get, deactivate, org isolation."""

import io

import pytest
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.services import customer_service
from app.utils.domain import normalize_domain


def test_normalize_domain():
    assert normalize_domain("https://www.Acme.com/") == "acme.com"
    assert normalize_domain("acme.com") == "acme.com"
    assert normalize_domain("  ") == ""


def test_detect_customer_csv_columns():
    m = customer_service.detect_customer_csv_columns(["domain", "company_name", "segment"])
    assert m["domain"] == 0
    assert m["company_name"] == 1
    assert m["segment"] == 2
    m2 = customer_service.detect_customer_csv_columns(["Website", "Name"])
    assert m2.get("domain") is not None
    assert m2.get("company_name") is not None


def test_upload_customers_csv_creates(db: Session, test_org: Organization):
    csv = b"domain,company_name,segment\nacme.com,Acme Corp,enterprise"
    result = customer_service.upload_customers_csv(db, test_org.id, csv)
    assert result.created == 1
    assert result.updated == 0
    assert result.skipped == 0
    items, total = customer_service.get_customers(db, test_org.id)
    assert total == 1
    assert items[0].domain == "acme.com"
    assert items[0].company_name == "Acme Corp"


def test_upload_customers_csv_updates(db: Session, test_org: Organization, test_customer):
    csv = f"domain,company_name\n{test_customer.domain},Updated Name".encode()
    result = customer_service.upload_customers_csv(db, test_org.id, csv)
    assert result.updated == 1
    db.refresh(test_customer)
    assert test_customer.company_name == "Updated Name"


def test_upload_customers_csv_skips_empty_domain(db: Session, test_org: Organization):
    csv = b"domain,company_name\n,No Domain"
    result = customer_service.upload_customers_csv(db, test_org.id, csv)
    assert result.skipped == 1


def test_get_customers_segment_filter(db: Session, test_org: Organization, test_customer):
    items, total = customer_service.get_customers(db, test_org.id, segment_filter="enterprise")
    assert total >= 1
    items, total = customer_service.get_customers(db, test_org.id, segment_filter="smb")
    assert total == 0


def test_get_customer_returns_none_other_org(db: Session, test_org: Organization, test_customer, second_org):
    c = customer_service.get_customer(db, second_org.id, test_customer.id)
    assert c is None


def test_deactivate_customer(db: Session, test_org: Organization, test_customer):
    ok = customer_service.deactivate_customer(db, test_org.id, test_customer.id)
    assert ok is True
    db.refresh(test_customer)
    assert test_customer.is_active is False
    items, _ = customer_service.get_customers(db, test_org.id)
    assert not any(x.id == test_customer.id for x in items)
