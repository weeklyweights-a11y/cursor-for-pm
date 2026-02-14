import pytest

from app.exceptions import AlreadyExistsError, AuthenticationError, NotFoundError
from app.services.auth_service import get_current_user, login, signup


def test_signup_with_valid_data_returns_user_org_and_token(db):
    """Signup with valid data creates org and user and returns token."""
    user, org, token = signup(
        db,
        email="new@example.com",
        password="password123",
        name="New User",
        organization_name="New Org",
    )
    assert user.email == "new@example.com"
    assert user.name == "New User"
    assert org.name == "New Org"
    assert org.slug
    assert token


def test_signup_with_duplicate_email_raises_already_exists(db, test_user):
    """Signup with existing email raises AlreadyExistsError."""
    with pytest.raises(AlreadyExistsError) as exc_info:
        signup(
            db,
            email=test_user.email,
            password="other123",
            name="Other",
            organization_name="Other Org",
        )
    assert "already exists" in str(exc_info.value.message).lower()


def test_login_with_valid_credentials_returns_user_and_token(db, test_user):
    """Login with valid email and password returns user and token."""
    user, token = login(db, "test@example.com", "password123")
    assert user.id == test_user.id
    assert token


def test_login_with_wrong_password_raises_authentication_error(db, test_user):
    """Login with wrong password raises AuthenticationError."""
    with pytest.raises(AuthenticationError):
        login(db, "test@example.com", "wrongpassword")


def test_login_with_nonexistent_email_raises_authentication_error(db):
    """Login with unknown email raises AuthenticationError."""
    with pytest.raises(AuthenticationError):
        login(db, "nobody@example.com", "password123")


def test_get_current_user_returns_user_when_found(db, test_user):
    """get_current_user returns user when id exists and active."""
    user = get_current_user(db, test_user.id)
    assert user.id == test_user.id


def test_get_current_user_raises_when_not_found(db):
    """get_current_user raises NotFoundError when user does not exist."""
    import uuid
    with pytest.raises(NotFoundError):
        get_current_user(db, uuid.uuid4())
