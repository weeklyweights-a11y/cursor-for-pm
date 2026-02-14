"""Tests for clustering routes."""

from unittest.mock import patch


def test_run_clustering_requires_auth(client):
    r = client.post("/api/v1/clustering/run")
    assert r.status_code == 401


def test_run_clustering_enqueues(client, auth_token):
    r = client.post("/api/v1/clustering/run", headers={"Authorization": f"Bearer {auth_token}"})
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert data["data"].get("status") == "enqueued"


def test_get_clustering_status_requires_auth(client):
    r = client.get("/api/v1/clustering/status")
    assert r.status_code == 401


def test_get_clustering_status_success(client, auth_token):
    r = client.get("/api/v1/clustering/status", headers={"Authorization": f"Bearer {auth_token}"})
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "is_running" in data["data"]
    assert "items_pending" in data["data"]
