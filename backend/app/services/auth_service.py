import re
import secrets
from uuid import UUID

from sqlalchemy.orm import Session

from app.exceptions import AlreadyExistsError, AuthenticationError, NotFoundError
from app.models.organization import Organization
from app.models.user import User
from app.utils.jwt import create_access_token
from app.utils.password import hash_password, verify_password


def _slugify(name: str) -> str:
    """Convert org name to URL-friendly slug (lowercase, alphanumeric and hyphens)."""
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s or "org"


def signup(
    db: Session,
    email: str,
    password: str,
    name: str,
    organization_name: str,
) -> tuple[User, Organization, str]:
    """
    Create organization and user, return user, org, and JWT.
    Raises AlreadyExistsError if email is already registered.
    """
    email = email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise AlreadyExistsError("A user with this email already exists.")

    base_slug = _slugify(organization_name)
    slug = base_slug
    counter = 0
    while db.query(Organization).filter(Organization.slug == slug).first():
        counter += 1
        slug = f"{base_slug}-{secrets.token_hex(2)}"

    org = Organization(name=organization_name, slug=slug)
    db.add(org)
    db.flush()

    user = User(
        email=email,
        name=name,
        hashed_password=hash_password(password),
        org_id=org.id,
    )
    db.add(user)
    db.commit()
    db.refresh(org)
    db.refresh(user)

    token = create_access_token(user.id, org.id)
    return user, org, token


def login(db: Session, email: str, password: str) -> tuple[User, str]:
    """
    Validate credentials and return user and JWT.
    Raises AuthenticationError if email not found or password wrong.
    """
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password.")

    if not user.is_active:
        raise AuthenticationError("Invalid email or password.")

    token = create_access_token(user.id, user.org_id)
    return user, token


def get_current_user(db: Session, user_id: UUID) -> User:
    """Load user by id. Raises NotFoundError if not found or inactive."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found.")
    if not user.is_active:
        raise NotFoundError("User not found.")
    return user
