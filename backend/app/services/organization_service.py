from uuid import UUID

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.organization import Organization


def get_organization(db: Session, org_id: UUID) -> Organization:
    """Return organization by id. Raises NotFoundError if not found."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundError("Organization not found.")
    return org


def update_organization(db: Session, org_id: UUID, name: str | None) -> Organization:
    """Update organization name. Returns updated org. Raises NotFoundError if not found."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundError("Organization not found.")
    if name is not None:
        org.name = name
    db.commit()
    db.refresh(org)
    return org
