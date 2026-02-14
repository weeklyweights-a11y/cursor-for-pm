import pytest

from app.exceptions import NotFoundError
from app.services.organization_service import get_organization, update_organization


def test_get_organization_returns_org_when_found(db, test_org):
    """get_organization returns org when id exists."""
    org = get_organization(db, test_org.id)
    assert org.id == test_org.id
    assert org.name == test_org.name


def test_get_organization_raises_when_not_found(db):
    """get_organization raises NotFoundError when org does not exist."""
    import uuid
    with pytest.raises(NotFoundError):
        get_organization(db, uuid.uuid4())


def test_update_organization_updates_name(db, test_org):
    """update_organization updates name and returns org."""
    updated = update_organization(db, test_org.id, "Updated Name")
    assert updated.name == "Updated Name"
