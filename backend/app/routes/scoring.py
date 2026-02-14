from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user_dependency
from app.models.user import User
from app.schemas.scoring import ScoringConfigResponse, ScoringConfigUpdateRequest
from app.services import scoring_service

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.get("/config")
def get_scoring_config(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Get current scoring config for org (create default if missing)."""
    config = scoring_service.get_scoring_config(db, current_user.org_id)
    return {"data": ScoringConfigResponse.model_validate(config).model_dump()}


@router.patch("/config")
def update_scoring_config(
    body: ScoringConfigUpdateRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Update goals, segments, weights. Weights must sum to 1.0; 422 if not."""
    try:
        config = scoring_service.update_scoring_config(
            db, current_user.org_id, body.model_dump(exclude_none=True)
        )
        return {"data": ScoringConfigResponse.model_validate(config).model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/re-score")
def re_score(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Recompute theme priority scores from current config."""
    scoring_service.score_themes(db, current_user.org_id)
    return {"data": {"status": "ok"}}
