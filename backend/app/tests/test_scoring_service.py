"""Tests for scoring service. Mocks LLM for strategic_fit."""

import pytest
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.theme import Theme
from app.services import scoring_service


def test_get_scoring_config_creates_default(db: Session, test_org: Organization):
    config = scoring_service.get_scoring_config(db, test_org.id)
    assert config is not None
    assert config.org_id == test_org.id
    assert abs(config.weight_volume + config.weight_reach + config.weight_urgency + config.weight_sentiment + config.weight_strategic_fit - 1.0) < 0.001


def test_update_scoring_config_valid_weights(db: Session, test_org: Organization, test_scoring_config):
    config = scoring_service.update_scoring_config(
        db, test_org.id,
        {"weight_volume": 0.3, "weight_reach": 0.2, "weight_urgency": 0.2, "weight_sentiment": 0.15, "weight_strategic_fit": 0.15},
    )
    assert config.weight_volume == 0.3


def test_update_scoring_config_weights_not_sum_one_raises(db: Session, test_org: Organization, test_scoring_config):
    with pytest.raises(ValueError, match="sum to 1.0"):
        scoring_service.update_scoring_config(
            db, test_org.id,
            {"weight_volume": 0.6, "weight_reach": 0.6, "weight_urgency": 0, "weight_sentiment": 0, "weight_strategic_fit": 0},
        )
