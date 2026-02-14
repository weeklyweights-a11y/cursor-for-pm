"""GAP 1: Column detection uses exact keyword table; content required."""

import pytest

from app.services.csv_service import (
    ContentColumnNotFoundError,
    detect_columns,
    parse_csv_row,
)


def test_detect_columns_content_required():
    """If no header matches content keywords, raise."""
    with pytest.raises(ContentColumnNotFoundError, match="feedback text"):
        detect_columns(["foo", "bar", "baz"])


def test_detect_columns_gap1_content_keywords():
    """GAP 1: content matches feedback, message, text, description, content, body, comment, note, request."""
    for header in ["feedback", "Feedback", "MESSAGE", "text", "description", "content", "body", "comment", "note", "request"]:
        m = detect_columns([header, "other"])
        assert "content" in m
        assert m["content"] == 0


def test_detect_columns_gap1_author_email():
    """GAP 1: author_email matches email, customer_email, user_email, requester_email, contact_email."""
    m = detect_columns(["feedback", "email"])
    assert m.get("author_email") == 1
    m = detect_columns(["feedback", "customer_email"])
    assert m.get("author_email") == 1


def test_detect_columns_gap1_author_name():
    """GAP 1: author_name matches name, customer_name, user_name, requester_name, contact_name, author."""
    m = detect_columns(["feedback", "name"])
    assert m.get("author_name") == 1
    m = detect_columns(["feedback", "author"])
    assert m.get("author_name") == 1


def test_detect_columns_gap1_organization_name():
    """GAP 1: organization_name matches company, customer, organization, org, account, company_name, org_name."""
    m = detect_columns(["feedback", "company"])
    assert m.get("organization_name") == 1


def test_detect_columns_gap1_timestamp():
    """GAP 1: timestamp matches date, created, created_at, timestamp, time, submitted, submitted_at."""
    m = detect_columns(["feedback", "date"])
    assert m.get("timestamp") == 1
    m = detect_columns(["feedback", "created_at"])
    assert m.get("timestamp") == 1


def test_detect_columns_case_insensitive():
    m = detect_columns(["FEEDBACK", "Email"])
    assert m["content"] == 0
    assert m["author_email"] == 1


def test_parse_csv_row():
    mapping = {"content": 0, "author_email": 1, "author_name": 2}
    row = ["Hello world", "a@b.com", "Alice"]
    out = parse_csv_row(row, mapping)
    assert out["content"] == "Hello world"
    assert out["author_email"] == "a@b.com"
    assert out["author_name"] == "Alice"


def test_parse_csv_row_empty_content():
    mapping = {"content": 0}
    row = [""]
    out = parse_csv_row(row, mapping)
    assert out["content"] is None
