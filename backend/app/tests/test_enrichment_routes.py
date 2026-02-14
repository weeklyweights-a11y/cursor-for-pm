"""Tests for enrichment routes: auth, re-enrich returns items_queued."""

import pytest
from fastapi.testclient import TestClient


def test_re_enrich_200(client: TestClient, auth_token: str):
    r = client.post(
        "/api/v1/enrichment/re-enrich",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert "items_queued" in data
    assert isinstance(data["items_queued"], int)


def test_re_enrich_requires_auth(client: TestClient):
    r = client.post("/api/v1/enrichment/re-enrich")
    assert r.status_code == 401
