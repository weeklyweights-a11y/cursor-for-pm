"""Embedding generation and similarity search (Phase 5)."""

from functools import lru_cache
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@lru_cache(maxsize=1)
def get_model():
    """Load sentence-transformers model once per process."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)


def generate_embedding(text: str) -> list[float] | None:
    """Return 384-d embedding for text, or None if empty."""
    if not (text and text.strip()):
        return None
    model = get_model()
    vec = model.encode(text.strip(), convert_to_numpy=True)
    return vec.tolist()


def generate_embeddings_batch(texts: list[str]) -> list[list[float] | None]:
    """Return list of 384-d embeddings; None for empty inputs."""
    if not texts:
        return []
    model = get_model()
    out: list[list[float] | None] = []
    for t in texts:
        if not (t and str(t).strip()):
            out.append(None)
            continue
        vec = model.encode(str(t).strip(), convert_to_numpy=True)
        out.append(vec.tolist())
    return out


def get_similar_items(
    db: "Session",
    org_id,
    embedding: list[float],
    limit: int = 10,
):
    """Query feedback_items by cosine distance to embedding; org-scoped."""
    from sqlalchemy import text

    from app.models.feedback_item import FeedbackItem

    if not embedding or len(embedding) != settings.embedding_dimension:
        return []
    emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
    sql = text(
        """
        SELECT id FROM feedback_items
        WHERE org_id = :org_id AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT :lim
        """
    )
    rows = db.execute(
        sql,
        {"org_id": str(org_id), "emb": emb_str, "lim": limit},
    ).fetchall()
    ids = [r[0] for r in rows]
    if not ids:
        return []
    return list(db.query(FeedbackItem).filter(FeedbackItem.id.in_(ids)).all())
