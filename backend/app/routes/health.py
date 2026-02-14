from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Check database connectivity. Returns 200 with status healthy or 503 unhealthy.
    """
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "environment": settings.environment,
            "version": "1.0.0",
        }
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy"})