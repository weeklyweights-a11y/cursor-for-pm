import os
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Generator

# Load .env.test from repo root when present (for pytest runs on host)
_env_test = Path(__file__).resolve().parent.parent.parent.parent / ".env.test"
if _env_test.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_test)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.organization import Organization
from app.models.user import User
from app.models.batch import Batch  # noqa: F401 - register for create_all
from app.models.customer import Customer  # noqa: F401
from app.models.domain_mapping import DomainMapping  # noqa: F401
from app.models.feedback_item import FeedbackItem  # noqa: F401
from app.models.match_review import MatchReviewQueue  # noqa: F401
from app.models.scoring_config import ScoringConfig  # noqa: F401
from app.models.slack_connection import SlackConnection  # noqa: F401
from app.models.theme import Theme  # noqa: F401
from app.utils.jwt import create_access_token
from app.utils.password import hash_password

# Use TEST_DATABASE_URL when set (e.g. running pytest on host: postgresql://...@127.0.0.1:5432/...).
# Otherwise use app settings (inside Docker: ...@db:5432/... works).
_test_db_url = os.environ.get("TEST_DATABASE_URL") or settings.database_url
engine = create_engine(_test_db_url, pool_pre_ping=True, poolclass=NullPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Table names for truncation (TestClient runs app in another thread, so we clean between tests.)
_TEST_TABLES = [
    "match_review_queue",
    "domain_mappings",
    "feedback_items",
    "themes",
    "scoring_configs",
    "customers",
    "slack_connections",
    "batches",
    "users",
    "product_contexts",
    "organizations",
]


def _truncate_all() -> None:
    """Truncate test tables so the next test sees a clean DB. Use a fresh connection."""
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE {} RESTART IDENTITY CASCADE".format(", ".join(_TEST_TABLES))))
        conn.commit()


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Yield a session in a transaction. Uses savepoints so app commit() only releases savepoint.
    Teardown rolls back and then truncates tables so the next test has a clean DB (covers
    the case where the app runs in another thread and commit() touched the real transaction).
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _truncate_all()
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False, autoflush=False)()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    session.begin_nested()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        _truncate_all()


@pytest.fixture
def client(db: Session):
    """Test client with get_db overridden to use the test session."""

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_org(db: Session) -> Organization:
    """Create a test organization."""
    org = Organization(name="Test Org", slug="test-org")
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def test_user(db: Session, test_org: Organization) -> User:
    """Create a test user in test_org."""
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password=hash_password("password123"),
        org_id=test_org.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user: User, test_org: Organization) -> str:
    """Return a valid JWT for test_user."""
    return create_access_token(test_user.id, test_org.id)


@pytest.fixture
def second_org(db: Session) -> Organization:
    """Create a second organization for isolation tests."""
    org = Organization(name="Other Org", slug="other-org")
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def second_user(db: Session, second_org: Organization) -> User:
    """Create a user in second_org."""
    user = User(
        email="other@example.com",
        name="Other User",
        hashed_password=hash_password("password123"),
        org_id=second_org.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def second_auth_token(second_user: User, second_org: Organization) -> str:
    """Valid JWT for second_user (Org B)."""
    return create_access_token(second_user.id, second_org.id)


@pytest.fixture
def test_customer(db: Session, test_org: Organization):
    """Create a test customer in test_org."""
    from app.models.customer import Customer
    customer = Customer(
        org_id=test_org.id,
        domain="acme.com",
        company_name="Acme Corp",
        segment="enterprise",
        is_active=True,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@pytest.fixture
def test_theme(db: Session, test_org: Organization) -> Theme:
    """Create a test theme in test_org."""
    theme = Theme(
        org_id=test_org.id,
        name="Test Theme",
        description="A test theme",
        mention_count=5,
        unique_customers=3,
        priority_score=0.75,
        is_current=True,
    )
    db.add(theme)
    db.commit()
    db.refresh(theme)
    return theme


@pytest.fixture
def test_scoring_config(db: Session, test_org: Organization) -> ScoringConfig:
    """Create default scoring config for test_org."""
    config = ScoringConfig(
        org_id=test_org.id,
        weight_volume=0.25,
        weight_reach=0.20,
        weight_urgency=0.25,
        weight_sentiment=0.15,
        weight_strategic_fit=0.15,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


# Dummy 384-d embedding for Phase 5 filter tests (no real model needed).
_SAMPLE_EMBEDDING = [0.1] * 384


@pytest.fixture
def sample_feedback_with_embedding(db: Session, test_org: Organization, test_theme: Theme):
    """Create three feedback items: one in a theme, one outlier, one unclustered.
    Returns a dict with theme_item, outlier_item, unclustered_item (FeedbackItem instances).
    """
    now = datetime.now(timezone.utc)
    theme_item = FeedbackItem(
        org_id=test_org.id,
        content="Feedback in theme",
        source_type="manual",
        source_id="embed-fixture-theme",
        embedding=_SAMPLE_EMBEDDING,
        theme_id=test_theme.id,
        is_outlier=False,
        clustered_at=now,
    )
    outlier_item = FeedbackItem(
        org_id=test_org.id,
        content="Outlier feedback",
        source_type="manual",
        source_id="embed-fixture-outlier",
        embedding=_SAMPLE_EMBEDDING,
        theme_id=None,
        is_outlier=True,
        clustered_at=now,
    )
    unclustered_item = FeedbackItem(
        org_id=test_org.id,
        content="Unclustered feedback",
        source_type="manual",
        source_id="embed-fixture-unclustered",
        embedding=_SAMPLE_EMBEDDING,
        theme_id=None,
        is_outlier=False,
        clustered_at=None,
    )
    for item in (theme_item, outlier_item, unclustered_item):
        db.add(item)
    db.commit()
    for item in (theme_item, outlier_item, unclustered_item):
        db.refresh(item)
    return {
        "theme_item": theme_item,
        "outlier_item": outlier_item,
        "unclustered_item": unclustered_item,
    }
