"""Tests for customer routes: auth, org isolation, status/body."""

import io

import pytest
from fastapi.testclient import TestClient

from app.models.organization import Organization


def test_upload_customers_csv_200(client: TestClient, auth_token: str):
    csv = b"domain,company_name,segment\nacme.com,Acme Corp,enterprise"
    r = client.post(
        "/api/v1/customers/upload",
        files={"file": ("customers.csv", io.BytesIO(csv), "text/csv")},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["created"] >= 1 or data["updated"] >= 1


def test_upload_customers_csv_no_domain_column_400(client: TestClient, auth_token: str):
    csv = b"foo,bar\n1,2"
    r = client.post(
        "/api/v1/customers/upload",
        files={"file": ("x.csv", io.BytesIO(csv), "text/csv")},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 400


def test_list_customers_200(client: TestClient, auth_token: str, test_customer):
    r = client.get(
        "/api/v1/customers",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert "data" in r.json()
    assert "pagination" in r.json()


def test_get_customer_200(client: TestClient, auth_token: str, test_customer):
    r = client.get(
        f"/api/v1/customers/{test_customer.id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["domain"] == test_customer.domain
    assert "feedback_count" in data


def test_get_customer_404_other_org(client: TestClient, second_auth_token: str, test_customer):
    r = client.get(
        f"/api/v1/customers/{test_customer.id}",
        headers={"Authorization": f"Bearer {second_auth_token}"},
    )
    assert r.status_code == 404


def test_customers_require_auth(client: TestClient):
    r = client.get("/api/v1/customers")
    assert r.status_code == 401
