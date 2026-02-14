"""Tests for clustering service. Mocks Redis and HDBSCAN where needed."""

from unittest.mock import patch

import numpy as np
import pytest
from sqlalchemy.orm import Session

from app.models.feedback_item import FeedbackItem
from app.models.organization import Organization
from app.models.theme import Theme
from app.services import clustering_service


def test_compute_centroid_empty():
    assert clustering_service.compute_centroid([]) is None


def test_compute_centroid_returns_mean():
    embs = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    c = clustering_service.compute_centroid(embs)
    assert c is not None
    assert len(c) == 3
    np.testing.assert_array_almost_equal(c, [1.0 / 3, 1.0 / 3, 1.0 / 3])


def test_should_recluster_below_threshold(db: Session, test_org: Organization):
    # No items with embedding and unclustered -> count 0
    result = clustering_service.should_recluster(db, test_org.id)
    assert result is False


def test_get_clustering_status_no_redis(db: Session, test_org: Organization):
    with patch.object(clustering_service, "_redis_client", return_value=None):
        status = clustering_service.get_clustering_status(db, test_org.id)
    assert status["is_running"] is False
    assert "items_pending" in status
