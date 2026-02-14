def test_get_organization_with_valid_token_returns_users_org(client, auth_token, test_org):
    """GET /organization with valid token returns the user's organization."""
    response = client.get(
        "/api/v1/organization",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"]["id"] == str(test_org.id)
    assert data["data"]["name"] == test_org.name


def test_patch_organization_updates_name(client, auth_token, test_org):
    """PATCH /organization with name updates the org name."""
    response = client.patch(
        "/api/v1/organization",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"name": "New Org Name"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "New Org Name"


def test_user_cannot_access_other_org_data(
    client, test_user, auth_token, second_org, second_auth_token
):
    """User A cannot see or modify Org B. GET returns only current user's org."""
    response = client.get(
        "/api/v1/organization",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(test_user.org_id)
    assert response.json()["data"]["id"] != str(second_org.id)

    client.patch(
        "/api/v1/organization",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"name": "Hacked"},
    )
    response_b = client.get(
        "/api/v1/organization",
        headers={"Authorization": f"Bearer {second_auth_token}"},
    )
    assert response_b.json()["data"]["name"] == "Other Org"
