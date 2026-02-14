import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.user import User


def test_manual_feedback_200(client: TestClient, auth_token: str, test_org: Organization):
    r = client.post(
        "/api/v1/feedback/manual",
        json={"content": "Manual feedback here"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["content"] == "Manual feedback here"
    assert data["source_type"] == "manual"


def test_manual_feedback_422_without_content(client: TestClient, auth_token: str):
    r = client.post(
        "/api/v1/feedback/manual",
        json={},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 422


def test_upload_csv_small_sync_completed(client: TestClient, auth_token: str):
    csv = b"feedback,email\nGreat product,user@example.com\nAnother one,a@b.com"
    r = client.post(
        "/api/v1/feedback/upload-csv",
        files={"file": ("test.csv", io.BytesIO(csv), "text/csv")},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["sync"] is True
    assert data["batch"]["status"] == "completed"
    assert data["batch"]["total_rows"] == 2


def test_upload_non_csv_400(client: TestClient, auth_token: str):
    r = client.post(
        "/api/v1/feedback/upload-csv",
        files={"file": ("x.txt", io.BytesIO(b"hello"), "text/plain")},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 400


def test_upload_csv_no_content_column_400(client: TestClient, auth_token: str):
    """GAP 1: when no header matches content keywords, return 400."""
    csv = b"foo,bar,baz\n1,2,3"
    r = client.post(
        "/api/v1/feedback/upload-csv",
        files={"file": ("test.csv", io.BytesIO(csv), "text/csv")},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 400
    detail = r.json().get("detail") or ""
    assert "feedback text" in detail or "column" in detail.lower()


def test_get_feedback_list(client: TestClient, auth_token: str):
    r = client.get(
        "/api/v1/feedback",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert "data" in r.json()
    assert "pagination" in r.json()


def test_get_feedback_list_filter_source_type(client: TestClient, auth_token: str):
    r = client.get(
        "/api/v1/feedback?source_type=manual",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200


def test_get_feedback_list_filter_theme_id(
    client: TestClient,
    auth_token: str,
    test_theme,
    sample_feedback_with_embedding,
):
    """Filter by theme_id returns only items in that theme."""
    r = client.get(
        f"/api/v1/feedback?theme_id={test_theme.id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    items = data["data"]
    pagination = data["pagination"]
    assert pagination["total"] == 1
    assert len(items) == 1
    assert items[0]["theme_id"] == str(test_theme.id)
    assert items[0]["content"] == "Feedback in theme"


def test_get_feedback_list_filter_outliers_only(
    client: TestClient,
    auth_token: str,
    sample_feedback_with_embedding,
):
    """outliers_only=true returns only outlier items."""
    r = client.get(
        "/api/v1/feedback?outliers_only=true",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    items = data["data"]
    pagination = data["pagination"]
    assert pagination["total"] == 1
    assert len(items) == 1
    assert items[0]["is_outlier"] is True
    assert items[0]["content"] == "Outlier feedback"


def test_get_feedback_list_filter_unclustered_only(
    client: TestClient,
    auth_token: str,
    sample_feedback_with_embedding,
):
    """unclustered_only=true returns only items with embedding but no theme/clustered_at."""
    r = client.get(
        "/api/v1/feedback?unclustered_only=true",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    items = data["data"]
    pagination = data["pagination"]
    assert pagination["total"] == 1
    assert len(items) == 1
    assert items[0]["theme_id"] is None
    assert items[0]["content"] == "Unclustered feedback"


def test_get_feedback_item_404(client: TestClient, auth_token: str):
    r = client.get(
        f"/api/v1/feedback/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 404


def test_feedback_org_isolation(
    client: TestClient,
    auth_token: str,
    second_auth_token: str,
    test_org: Organization,
):
    # Create as first org
    r1 = client.post(
        "/api/v1/feedback/manual",
        json={"content": "Org A feedback"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r1.status_code == 200
    item_id = r1.json()["data"]["id"]
    # Second org cannot see it
    r2 = client.get(
        f"/api/v1/feedback/{item_id}",
        headers={"Authorization": f"Bearer {second_auth_token}"},
    )
    assert r2.status_code == 404
