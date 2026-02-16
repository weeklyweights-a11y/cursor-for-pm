"""Tests for brief API routes (Phase 7)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.brief import Brief
from app.models.organization import Organization
from app.models.theme import Theme


def test_post_generate_creates_brief_and_returns_id(
    client: TestClient, auth_token: str, test_theme: Theme
):
    with patch("app.tasks.brief_tasks.generate_brief_task") as mock_task:
        mock_task.delay.return_value = None
        r = client.post(
            "/api/v1/briefs/generate",
            json={"theme_id": str(test_theme.id)},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert r.status_code == 200
    data = r.json()["data"]
    assert "brief_id" in data
    assert data["status"] == "generating"


def test_post_generate_theme_not_found_404(client: TestClient, auth_token: str):
    import uuid
    r = client.post(
        "/api/v1/briefs/generate",
        json={"theme_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 404


def test_get_brief_returns_sections(
    client: TestClient, auth_token: str, sample_brief: Brief
):
    r = client.get(
        f"/api/v1/briefs/{sample_brief.id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["id"] == str(sample_brief.id)
    assert "sections" in data
    assert len(data["sections"]) >= 1


def test_get_brief_other_org_404(
    client: TestClient, second_auth_token: str, sample_brief: Brief
):
    r = client.get(
        f"/api/v1/briefs/{sample_brief.id}",
        headers={"Authorization": f"Bearer {second_auth_token}"},
    )
    assert r.status_code == 404


def test_get_brief_status(client: TestClient, auth_token: str, sample_brief: Brief):
    r = client.get(
        f"/api/v1/briefs/{sample_brief.id}/status",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["brief_id"] == str(sample_brief.id)
    assert "sections_completed" in data
    assert "sections_total" in data


def test_get_briefs_for_theme(
    client: TestClient, auth_token: str, test_theme: Theme, sample_brief: Brief
):
    r = client.get(
        f"/api/v1/briefs/theme/{test_theme.id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list)
    assert any(b["id"] == str(sample_brief.id) for b in data)


def test_get_current_brief_for_theme(
    client: TestClient, auth_token: str, test_theme: Theme, sample_brief: Brief
):
    r = client.get(
        f"/api/v1/briefs/theme/{test_theme.id}/current",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["id"] == str(sample_brief.id)


def test_patch_section_updates_content(
    client: TestClient, auth_token: str, sample_brief: Brief
):
    r = client.patch(
        f"/api/v1/briefs/{sample_brief.id}/sections/problem_statement",
        json={"content": "Edited content"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    sec = next(s for s in data["sections"] if s["key"] == "problem_statement")
    assert sec["content"] == "Edited content"
    assert sec.get("edited") is True


def test_post_regenerate_section(
    client: TestClient, auth_token: str, sample_brief: Brief
):
    with patch("app.services.brief_service.brief_section_generators.generate_problem_statement", return_value="New content."):
        r = client.post(
            f"/api/v1/briefs/{sample_brief.id}/sections/problem_statement/regenerate",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert r.status_code == 200


def test_post_evaluate_solution(
    client: TestClient, auth_token: str, sample_brief: Brief
):
    with patch("app.services.brief_service.brief_section_generators.evaluate_solution_against_evidence") as mock_eval:
        mock_eval.return_value = {
            "pain_points_addressed": [],
            "coverage_score": 0.5,
            "strengths": [],
            "gaps": [],
        }
        r = client.post(
            f"/api/v1/briefs/{sample_brief.id}/evaluate-solution",
            json={"solution_description": "We will add SSO."},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert r.status_code == 200
    assert r.json()["data"].get("solution_evaluation") is not None


def test_get_export_markdown(client: TestClient, auth_token: str, sample_brief: Brief):
    r = client.get(
        f"/api/v1/briefs/{sample_brief.id}/export/markdown",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert "markdown_content" in data
    assert "filename" in data


def test_briefs_require_auth(client: TestClient, sample_brief: Brief):
    r = client.get(f"/api/v1/briefs/{sample_brief.id}")
    assert r.status_code == 401
