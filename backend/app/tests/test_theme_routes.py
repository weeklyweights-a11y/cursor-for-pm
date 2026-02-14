"""Tests for theme routes. Auth and org-scoping."""

import pytest


def test_list_themes_requires_auth(client):
    r = client.get("/api/v1/themes")
    assert r.status_code == 401


def test_list_themes_success(client, auth_token):
    r = client.get("/api/v1/themes", headers={"Authorization": f"Bearer {auth_token}"})
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "pagination" in data


def test_get_theme_requires_auth(client, test_theme):
    r = client.get(f"/api/v1/themes/{test_theme.id}")
    assert r.status_code == 401


def test_get_theme_success(client, auth_token, test_theme):
    r = client.get(f"/api/v1/themes/{test_theme.id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "Test Theme"


def test_get_theme_other_org_404(client, second_auth_token, test_theme):
    r = client.get(f"/api/v1/themes/{test_theme.id}", headers={"Authorization": f"Bearer {second_auth_token}"})
    assert r.status_code == 404


def test_get_theme_feedback_success(client, auth_token, test_theme):
    r = client.get(f"/api/v1/themes/{test_theme.id}/feedback", headers={"Authorization": f"Bearer {auth_token}"})
    assert r.status_code == 200
    assert "data" in r.json()
