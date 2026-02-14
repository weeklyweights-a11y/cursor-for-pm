import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.services import batch_service


def test_get_batches(client: TestClient, auth_token: str, db: Session, test_org: Organization):
    batch_service.create_batch(db, test_org.id, "a.csv", 5)
    r = client.get(
        "/api/v1/batches",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) >= 1


def test_get_batch_by_id(client: TestClient, auth_token: str, db: Session, test_org: Organization):
    batch = batch_service.create_batch(db, test_org.id, "b.csv", 10)
    r = client.get(
        f"/api/v1/batches/{batch.id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["id"] == str(batch.id)
    assert r.json()["data"]["filename"] == "b.csv"


def test_get_batch_404(client: TestClient, auth_token: str):
    r = client.get(
        f"/api/v1/batches/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 404


def test_get_batch_org_isolation(
    client: TestClient,
    auth_token: str,
    second_auth_token: str,
    db: Session,
    test_org: Organization,
    second_org: Organization,
):
    batch = batch_service.create_batch(db, test_org.id, "org1.csv", 1)
    r = client.get(
        f"/api/v1/batches/{batch.id}",
        headers={"Authorization": f"Bearer {second_auth_token}"},
    )
    assert r.status_code == 404
