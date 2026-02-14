from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base  # noqa: F401 - import so Alembic sees models
from app.models.batch import Batch  # noqa: F401
from app.models.customer import Customer  # noqa: F401
from app.models.domain_mapping import DomainMapping  # noqa: F401
from app.models.feedback_item import FeedbackItem  # noqa: F401
from app.models.match_review import MatchReviewQueue  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.product_context import ProductContext  # noqa: F401
from app.models.scoring_config import ScoringConfig  # noqa: F401
from app.models.slack_connection import SlackConnection  # noqa: F401
from app.models.theme import Theme  # noqa: F401
from app.models.user import User  # noqa: F401

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session. Closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
