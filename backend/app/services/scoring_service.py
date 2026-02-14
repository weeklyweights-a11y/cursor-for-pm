"""Scoring config and theme scoring (Phase 5)."""

from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.scoring_config import ScoringConfig
from app.models.theme import Theme
from app.services.llm_service import call_llm

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_DEFAULT_WEIGHTS = {
    "weight_volume": 0.25,
    "weight_reach": 0.20,
    "weight_urgency": 0.25,
    "weight_sentiment": 0.15,
    "weight_strategic_fit": 0.15,
}


def get_scoring_config(db: Session, org_id: UUID) -> ScoringConfig:
    """Get or create default scoring config for org."""
    config = db.query(ScoringConfig).filter(ScoringConfig.org_id == org_id).first()
    if config:
        return config
    config = ScoringConfig(org_id=org_id, **_DEFAULT_WEIGHTS)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def update_scoring_config(db: Session, org_id: UUID, data: dict) -> ScoringConfig:
    """Update config; validate weights sum to 1.0 (±0.001); then score_themes."""
    config = get_scoring_config(db, org_id)
    if "goals" in data and data["goals"] is not None:
        config.goals = data["goals"]
    if "target_segments" in data and data["target_segments"] is not None:
        config.target_segments = data["target_segments"]
    for k in ["weight_volume", "weight_reach", "weight_urgency", "weight_sentiment", "weight_strategic_fit"]:
        if k in data and data[k] is not None:
            setattr(config, k, float(data[k]))
    total = config.weight_volume + config.weight_reach + config.weight_urgency + config.weight_sentiment + config.weight_strategic_fit
    if abs(total - 1.0) > 0.001:
        raise ValueError("Weights must sum to 1.0")
    db.commit()
    db.refresh(config)
    score_themes(db, org_id)
    return config


def _strategic_fit_scores(goals: list[str] | None, target_segments: list[str] | None, themes: list[Theme]) -> list[float]:
    """Call LLM for strategic fit; return list of scores (0–1) per theme."""
    if not themes:
        return []
    if not goals and not target_segments:
        return [0.5] * len(themes)
    system_path = _PROMPTS_DIR / "strategic_fit_system.txt"
    user_path = _PROMPTS_DIR / "strategic_fit_user.txt"
    system = system_path.read_text().strip()
    template = user_path.read_text().strip()
    goals_str = ", ".join(goals or [])
    segments_str = ", ".join(target_segments or [])
    themes_block = "\n".join(f"{i}. {t.name}: {t.description or ''}" for i, t in enumerate(themes))
    prompt = template.format(goals=goals_str, target_segments=segments_str, themes_block=themes_block)
    try:
        result, _ = call_llm(prompt, system, temperature=0.2, max_tokens=1024)
        if isinstance(result, list):
            by_idx = {int(x.get("theme_index", i)): float(x.get("score", 0.5)) for i, x in enumerate(result)}
            return [by_idx.get(i, 0.5) for i in range(len(themes))]
        return [0.5] * len(themes)
    except Exception:
        return [0.5] * len(themes)


def score_themes(db: Session, org_id: UUID) -> None:
    """Load current themes and config; compute 5 factors; store priority_score and score_breakdown."""
    config = get_scoring_config(db, org_id)
    themes = db.query(Theme).filter(Theme.org_id == org_id, Theme.is_current == True).all()
    if not themes:
        return
    mention_max = max((t.mention_count for t in themes), default=1)
    customers_max = max((t.unique_customers for t in themes), default=1)
    urgency_map = {"low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}
    strategic = _strategic_fit_scores(config.goals, config.target_segments, themes)
    for i, theme in enumerate(themes):
        vol_norm = theme.mention_count / mention_max if mention_max else 0
        reach_norm = theme.unique_customers / customers_max if customers_max else 0
        urgency_norm = 0.5
        if theme.urgency_breakdown:
            u = theme.urgency_breakdown
            total = sum(u.values()) or 1
            urgency_norm = sum(urgency_map.get(k, 0.5) * (v / total) for k, v in u.items())
        sent_norm = 0.5
        if theme.sentiment_breakdown:
            s = theme.sentiment_breakdown
            neg = s.get("negative") or 0
            total = sum(s.values()) or 1
            sent_norm = 1.0 - (neg / total)
        wv, wr, wu, ws, wf = config.weight_volume, config.weight_reach, config.weight_urgency, config.weight_sentiment, config.weight_strategic_fit
        weighted_vol = vol_norm * wv
        weighted_reach = reach_norm * wr
        weighted_urg = urgency_norm * wu
        weighted_sent = sent_norm * ws
        weighted_fit = strategic[i] * wf
        priority = weighted_vol + weighted_reach + weighted_urg + weighted_sent + weighted_fit
        theme.priority_score = priority
        theme.score_breakdown = {
            "volume": {"raw": theme.mention_count, "normalized": vol_norm, "weighted": weighted_vol},
            "reach": {"raw": theme.unique_customers, "normalized": reach_norm, "weighted": weighted_reach},
            "urgency": {"raw": None, "normalized": urgency_norm, "weighted": weighted_urg},
            "sentiment": {"raw": None, "normalized": sent_norm, "weighted": weighted_sent},
            "strategic_fit": {"raw": strategic[i], "normalized": strategic[i], "weighted": weighted_fit},
        }
    db.commit()
