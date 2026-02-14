def test_signup_with_valid_data_returns_200_with_user_org_and_token(client):
    """POST /auth/signup with valid body returns 200 and data with user, org, token."""
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "signup@example.com",
            "password": "password123",
            "name": "Signup User",
            "organization_name": "Signup Org",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"]["user"]["email"] == "signup@example.com"
    assert data["data"]["organization"]["name"] == "Signup Org"
    assert data["data"]["access_token"]


def test_signup_with_duplicate_email_returns_400(client, test_user):
    """POST /auth/signup with existing email returns 400."""
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": test_user.email,
            "password": "password123",
            "name": "Duplicate",
            "organization_name": "Dup Org",
        },
    )
    assert response.status_code == 400
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "ALREADY_EXISTS"


def test_login_with_valid_credentials_returns_200_with_token(client, test_user):
    """POST /auth/login with valid credentials returns 200 and token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]
    assert response.json()["data"]["user"]["email"] == "test@example.com"


def test_login_with_wrong_password_returns_401(client, test_user):
    """POST /auth/login with wrong password returns 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_with_nonexistent_email_returns_401(client):
    """POST /auth/login with unknown email returns 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert response.status_code == 401


def test_get_me_with_valid_token_returns_user(client, auth_token):
    """GET /auth/me with valid Bearer token returns current user."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "test@example.com"


def test_get_me_without_token_returns_401(client):
    """GET /auth/me without Authorization header returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_get_me_with_invalid_token_returns_401(client):
    """GET /auth/me with invalid token returns 401."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
