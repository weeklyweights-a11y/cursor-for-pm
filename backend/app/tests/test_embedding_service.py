"""Tests for embedding service. Mocks sentence-transformers model."""

from unittest.mock import patch, MagicMock

import pytest

from app.services import embedding_service


@patch.object(embedding_service, "get_model")
def test_generate_embedding_returns_384d(mock_get_model):
    mock_get_model.return_value = MagicMock(encode=lambda x, **kw: [0.1] * 384)
    result = embedding_service.generate_embedding("hello world")
    assert result is not None
    assert len(result) == 384


def test_generate_embedding_empty_returns_none():
    assert embedding_service.generate_embedding("") is None
    assert embedding_service.generate_embedding("   ") is None


@patch.object(embedding_service, "get_model")
def test_generate_embeddings_batch(mock_get_model):
    mock_get_model.return_value = MagicMock(encode=lambda x, **kw: [0.0] * 384)
    result = embedding_service.generate_embeddings_batch(["a", "b"])
    assert len(result) == 2
    assert all(len(r) == 384 for r in result if r is not None)


def test_generate_embeddings_batch_empty_input():
    assert embedding_service.generate_embeddings_batch([]) == []
