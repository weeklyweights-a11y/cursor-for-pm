"""Tests for spec API routes (Phase 8)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.models.brief import Brief
from app.models.organization import Organization
from app.models.spec import Spec
from app.models.theme import Theme


def test_post_generate_creates_spec_and_returns_id(
    client: TestClient,
    auth_token: str,
    sample_brief_with_evaluation: Brief,
):
    with patch("app.tasks.spec_tasks.generate_spec_task") as mock_task:
        mock_task.delay.return_value = None
        r = client.post(
            "/api/v1/specs/generate",
            json={
                "brief_id": str(sample_brief_with_evaluation.id),
                "scope": "full",
                "target_audience": "mixed",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert r.status_code == 200
    data = r.json()["data"]
    assert "spec_id" in data
    assert data["status"] == "generating"


def test_post_generate_without_solution_evaluation_400(
    client: TestClient, auth_token: str, sample_brief: Brief
):
    """Brief without solution_evaluation returns 400."""
    r = client.post(
        "/api/v1/specs/generate",
        json={
            "brief_id": str(sample_brief.id),
            "scope": "full",
            "target_audience": "mixed",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 400


def test_post_generate_brief_not_found_400(client: TestClient, auth_token: str):
    import uuid
    r = client.post(
        "/api/v1/specs/generate",
        json={
            "brief_id": str(uuid.uuid4()),
            "scope": "full",
            "target_audience": "mixed",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 400


def test_get_spec_returns_sections(
    client: TestClient, auth_token: str, sample_spec: Spec
):
    r = client.get(
        f"/api/v1/specs/{sample_spec.id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["id"] == str(sample_spec.id)
    assert "sections" in data
    assert len(data["sections"]) >= 1


def test_get_spec_other_org_404(
    client: TestClient, second_auth_token: str, sample_spec: Spec
):
    r = client.get(
        f"/api/v1/specs/{sample_spec.id}",
        headers={"Authorization": f"Bearer {second_auth_token}"},
    )
    assert r.status_code == 404


def test_get_spec_status(
    client: TestClient, auth_token: str, sample_spec: Spec
):
    r = client.get(
        f"/api/v1/specs/{sample_spec.id}/status",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["spec_id"] == str(sample_spec.id)
    assert "sections_completed" in data
    assert "sections_total" in data


def test_get_specs_for_brief(
    client: TestClient,
    auth_token: str,
    sample_brief_with_evaluation: Brief,
    sample_spec: Spec,
):
    r = client.get(
        f"/api/v1/specs/brief/{sample_brief_with_evaluation.id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list)
    assert any(s["id"] == str(sample_spec.id) for s in data)


def test_get_current_spec_for_brief(
    client: TestClient,
    auth_token: str,
    sample_brief_with_evaluation: Brief,
    sample_spec: Spec,
):
    r = client.get(
        f"/api/v1/specs/brief/{sample_brief_with_evaluation.id}/current",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["id"] == str(sample_spec.id)


def test_get_specs_for_theme(
    client: TestClient, auth_token: str, test_theme: Theme, sample_spec: Spec
):
    r = client.get(
        f"/api/v1/specs/theme/{test_theme.id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list)
    assert any(s["id"] == str(sample_spec.id) for s in data)


def test_patch_section_updates_content(
    client: TestClient, auth_token: str, sample_spec: Spec
):
    r = client.patch(
        f"/api/v1/specs/{sample_spec.id}/sections/executive_summary",
        json={"content": "Edited summary"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    sec = next(s for s in data["sections"] if s["key"] == "executive_summary")
    assert sec["content"] == "Edited summary"
    assert sec.get("edited") is True


def test_post_regenerate_section(
    client: TestClient, auth_token: str, sample_spec: Spec
):
    with patch(
        "app.services.spec_service.spec_section_generators.generate_executive_summary",
        return_value="New summary.",
    ):
        r = client.post(
            f"/api/v1/specs/{sample_spec.id}/sections/executive_summary/regenerate",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert r.status_code == 200


def test_get_export_markdown(client: TestClient, auth_token: str, sample_spec: Spec):
    r = client.get(
        f"/api/v1/specs/{sample_spec.id}/export/markdown",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert "markdown_content" in data
    assert "filename" in data
    assert data.get("format") == "standard"


def test_get_export_cursor(client: TestClient, auth_token: str, sample_spec: Spec):
    r = client.get(
        f"/api/v1/specs/{sample_spec.id}/export/cursor",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert "markdown_content" in data
    assert "filename" in data
    assert data.get("format") == "cursor"


def test_specs_require_auth(client: TestClient, sample_spec: Spec):
    r = client.get(f"/api/v1/specs/{sample_spec.id}")
    assert r.status_code == 401
