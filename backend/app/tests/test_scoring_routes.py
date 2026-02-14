"""Tests for scoring routes."""


def test_get_scoring_config_requires_auth(client):
    r = client.get("/api/v1/scoring/config")
    assert r.status_code == 401


def test_get_scoring_config_success(client, auth_token):
    r = client.get("/api/v1/scoring/config", headers={"Authorization": f"Bearer {auth_token}"})
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "weight_volume" in data["data"]


def test_patch_scoring_config_valid(client, auth_token):
    r = client.patch(
        "/api/v1/scoring/config",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"weight_volume": 0.3, "weight_reach": 0.2, "weight_urgency": 0.2, "weight_sentiment": 0.15, "weight_strategic_fit": 0.15},
    )
    assert r.status_code == 200


def test_patch_scoring_config_weights_dont_sum_422(client, auth_token):
    r = client.patch(
        "/api/v1/scoring/config",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"weight_volume": 0.6, "weight_reach": 0.6, "weight_urgency": 0, "weight_sentiment": 0, "weight_strategic_fit": 0},
    )
    assert r.status_code == 422


def test_re_score_requires_auth(client):
    r = client.post("/api/v1/scoring/re-score")
    assert r.status_code == 401


def test_re_score_success(client, auth_token):
    r = client.post("/api/v1/scoring/re-score", headers={"Authorization": f"Bearer {auth_token}"})
    assert r.status_code == 200
