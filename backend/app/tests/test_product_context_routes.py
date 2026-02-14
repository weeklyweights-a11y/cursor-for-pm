"""Tests for product context routes. POST/GET/PATCH; 404 when missing; other org inaccessible."""

import pytest
from fastapi.testclient import TestClient

from app.models.organization import Organization


def test_get_product_context_404(client: TestClient, auth_token: str):
    r = client.get(
        "/api/v1/product-context",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 404


def test_post_product_context_200(client: TestClient, auth_token: str):
    r = client.post(
        "/api/v1/product-context",
        json={
            "product_name": "My Product",
            "product_description": "Does things",
            "existing_features": ["Search"],
            "target_users": "PMs",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["product_name"] == "My Product"
    assert data["existing_features"] == ["Search"]


def test_post_product_context_already_exists_400(client: TestClient, auth_token: str):
    client.post(
        "/api/v1/product-context",
        json={"product_name": "P", "product_description": "D"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    r = client.post(
        "/api/v1/product-context",
        json={"product_name": "P2", "product_description": "D2"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 400


def test_get_product_context_200_after_create(client: TestClient, auth_token: str):
    client.post(
        "/api/v1/product-context",
        json={"product_name": "P", "product_description": "D"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    r = client.get(
        "/api/v1/product-context",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["product_name"] == "P"


def test_patch_product_context_200(client: TestClient, auth_token: str):
    client.post(
        "/api/v1/product-context",
        json={"product_name": "P", "product_description": "D"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    r = client.patch(
        "/api/v1/product-context",
        json={"product_name": "P Updated"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["product_name"] == "P Updated"


def test_patch_product_context_404_when_missing(client: TestClient, auth_token: str):
    r = client.patch(
        "/api/v1/product-context",
        json={"product_name": "P"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 404


def test_product_context_other_org_cannot_access(
    client: TestClient,
    auth_token: str,
    second_auth_token: str,
):
    client.post(
        "/api/v1/product-context",
        json={"product_name": "Org A Product", "product_description": "D"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    r = client.get(
        "/api/v1/product-context",
        headers={"Authorization": f"Bearer {second_auth_token}"},
    )
    assert r.status_code == 404
