"""Clustering: should_recluster, run_clustering, status (Phase 5)."""

import json
import time
from datetime import datetime, timezone
from uuid import UUID

import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.models.feedback_item import FeedbackItem
from app.models.theme import Theme
from app.services.scoring_service import score_themes
from app.services.theme_service import name_theme_from_quotes

try:
    import redis
except ImportError:
    redis = None  # type: ignore[assignment]


def _redis_client():
    if redis is None:
        return None
    return redis.from_url(settings.redis_url)


def should_recluster(db: Session, org_id: UUID) -> bool:
    """True if count of items with embedding and no theme_id/clustered_at >= recluster_threshold."""
    from sqlalchemy import and_, func

    count = (
        db.query(func.count(FeedbackItem.id))
        .filter(
            FeedbackItem.org_id == org_id,
            FeedbackItem.embedding.isnot(None),
            (FeedbackItem.theme_id.is_(None)) & (FeedbackItem.clustered_at.is_(None)),
        )
        .scalar()
        or 0
    )
    return count >= settings.recluster_threshold


def compute_centroid(embeddings: list[list[float]]) -> list[float] | None:
    """Numpy mean of embeddings; None if empty."""
    if not embeddings:
        return None
    arr = np.array(embeddings, dtype=np.float64)
    return np.mean(arr, axis=0).tolist()


def compute_cluster_stats(db: Session, org_id: UUID, item_ids: list[UUID]) -> dict:
    """mention_count, unique_customers, segment/urgency/sentiment breakdowns from items."""
    items = db.query(FeedbackItem).filter(FeedbackItem.org_id == org_id, FeedbackItem.id.in_(item_ids)).all()
    mention_count = len(items)
    unique_customers = len({i.customer_id for i in items if i.customer_id})
    segment_breakdown = {}
    urgency_breakdown = {}
    sentiment_breakdown = {}
    for i in items:
        if i.segment:
            segment_breakdown[i.segment] = segment_breakdown.get(i.segment, 0) + 1
        if i.urgency:
            urgency_breakdown[i.urgency] = urgency_breakdown.get(i.urgency, 0) + 1
        if i.sentiment:
            sentiment_breakdown[i.sentiment] = sentiment_breakdown.get(i.sentiment, 0) + 1
    return {
        "mention_count": mention_count,
        "unique_customers": unique_customers,
        "segment_breakdown": segment_breakdown or None,
        "urgency_breakdown": urgency_breakdown or None,
        "sentiment_breakdown": sentiment_breakdown or None,
    }


def _cosine_distance(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a, dtype=np.float64)
    b_arr = np.array(b, dtype=np.float64)
    return float(1.0 - np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr) + 1e-12))


def select_top_quotes(items: list[FeedbackItem], centroid: list[float], n: int = 5) -> list[str]:
    """By cosine distance to centroid; return up to n quote strings."""
    with_embedding = [(i, i.embedding) for i in items if i.embedding is not None and isinstance(i.embedding, (list, np.ndarray))]
    if not with_embedding or not centroid:
        quotes = []
        for i in items[:n]:
            q = (i.verbatim_quote or i.pain_point or i.content or "").strip()
            if q:
                quotes.append(q[:500])
        return quotes[:n]
    emb_list = [list(e) if hasattr(e, "__iter__") and not isinstance(e, str) else e for _, e in with_embedding]
    dists = [_cosine_distance(emb, centroid) for emb in emb_list]
    idx = np.argsort(dists)[:n]
    quotes = []
    for j in idx:
        i = with_embedding[j][0]
        q = (i.verbatim_quote or i.pain_point or i.content or "").strip()
        if q:
            quotes.append(q[:500])
    return quotes[:n]


def set_clustering_running(org_id: UUID, running: bool) -> None:
    """Set or delete Redis key clustering:running:{org_id}."""
    client = _redis_client()
    if not client:
        return
    key = f"clustering:running:{org_id}"
    if running:
        client.set(key, "1")
    else:
        client.delete(key)


def run_clustering(db: Session, org_id: UUID) -> dict:
    """HDBSCAN; create themes; assign items; score; write last_run to Redis. Return summary."""
    import hdbscan

    start = time.perf_counter()
    items = (
        db.query(FeedbackItem)
        .filter(FeedbackItem.org_id == org_id, FeedbackItem.embedding.isnot(None))
        .all()
    )
    if not items:
        duration_ms = int((time.perf_counter() - start) * 1000)
        _write_last_run(org_id, 0, 0, len(items), duration_ms)
        return {"clusters_found": 0, "outliers": 0, "items_processed": 0, "duration_ms": duration_ms}
    embeddings = []
    for i in items:
        e = i.embedding
        if e is not None:
            embeddings.append(list(e) if hasattr(e, "__iter__") and not isinstance(e, str) else e)
        else:
            embeddings.append([0.0] * settings.embedding_dimension)
    X = np.array(embeddings, dtype=np.float64)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=settings.hdbscan_min_cluster_size,
        min_samples=settings.hdbscan_min_samples,
        metric="euclidean",
    )
    labels = clusterer.fit_predict(X)
    db.query(Theme).filter(Theme.org_id == org_id).update({"is_current": False})
    cluster_ids = set(labels) - {-1}
    clusters_found = len(cluster_ids)
    outliers = int((labels == -1).sum())
    now = datetime.now(timezone.utc)
    for cid in cluster_ids:
        mask = labels == cid
        item_subset = [items[j] for j in range(len(items)) if mask[j]]
        item_ids = [i.id for i in item_subset]
        embs = [embeddings[j] for j in range(len(items)) if mask[j]]
        centroid = compute_centroid(embs)
        stats = compute_cluster_stats(db, org_id, item_ids)
        top_quotes = select_top_quotes(item_subset, centroid or [], 5)
        name, description = name_theme_from_quotes(top_quotes, f"Theme {cid}", "Cluster of related feedback.")
        theme = Theme(
            org_id=org_id,
            name=name,
            description=description,
            centroid=centroid,
            mention_count=stats["mention_count"],
            unique_customers=stats["unique_customers"],
            segment_breakdown=stats["segment_breakdown"],
            urgency_breakdown=stats["urgency_breakdown"],
            sentiment_breakdown=stats["sentiment_breakdown"],
            top_quotes=top_quotes or None,
            is_current=True,
        )
        db.add(theme)
        db.flush()
        for i in item_subset:
            i.theme_id = theme.id
            i.is_outlier = False
            i.clustered_at = now
    for j, i in enumerate(items):
        if labels[j] == -1:
            i.theme_id = None
            i.is_outlier = True
            i.clustered_at = now
    db.commit()
    score_themes(db, org_id)
    duration_ms = int((time.perf_counter() - start) * 1000)
    _write_last_run(org_id, clusters_found, outliers, len(items), duration_ms)
    return {"clusters_found": clusters_found, "outliers": outliers, "items_processed": len(items), "duration_ms": duration_ms}


def _write_last_run(org_id: UUID, clusters_found: int, outliers: int, items_processed: int, duration_ms: int) -> None:
    client = _redis_client()
    if not client:
        return
    key = f"clustering:last_run:{org_id}"
    payload = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "clusters_found": clusters_found,
        "outliers": outliers,
        "duration_ms": duration_ms,
    }
    client.set(key, json.dumps(payload))


def get_clustering_status(db: Session, org_id: UUID) -> dict:
    """is_running from Redis; last_run from Redis; items_pending from DB."""
    from sqlalchemy import and_, func

    client = _redis_client()
    is_running = False
    last_run_result = None
    if client:
        rkey = f"clustering:running:{org_id}"
        is_running = client.get(rkey) == "1" or client.get(rkey) == b"1"
        lrkey = f"clustering:last_run:{org_id}"
        raw = client.get(lrkey)
        if raw:
            try:
                last_run_result = json.loads(raw if isinstance(raw, str) else raw.decode())
            except Exception:
                pass
    items_pending = (
        db.query(func.count(FeedbackItem.id))
        .filter(
            FeedbackItem.org_id == org_id,
            FeedbackItem.embedding.isnot(None),
            FeedbackItem.theme_id.is_(None),
            FeedbackItem.clustered_at.is_(None),
        )
        .scalar()
        or 0
    )
    last_run_at = None
    if last_run_result and "completed_at" in last_run_result:
        try:
            last_run_at = datetime.fromisoformat(last_run_result["completed_at"].replace("Z", "+00:00"))
        except Exception:
            pass
    return {
        "is_running": is_running,
        "last_run_at": last_run_at,
        "last_run_result": last_run_result,
        "items_pending": items_pending,
    }
