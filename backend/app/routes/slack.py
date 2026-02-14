import hashlib
import hmac
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user_dependency
from app.models.user import User
from app.schemas.slack import (
    SlackChannelResponse,
    SlackChannelSelectRequest,
    SlackConnectionStatusResponse,
)
from app.services import slack_service
from app.tasks.slack_tasks import process_slack_event

router = APIRouter(prefix="/slack", tags=["slack"])


def _verify_slack_signature(body: bytes, signature: str | None) -> bool:
    """Verify X-Slack-Signature: v0=<hmac_sha256_hex>."""
    if not signature or not settings.slack_signing_secret:
        return False
    if not signature.startswith("v0="):
        return False
    expected = "v0=" + hmac.new(
        settings.slack_signing_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _should_enqueue_message(event: dict) -> bool:
    """GAP 2: Skip bot, message_changed/message_deleted; only type==message with no subtype."""
    if event.get("bot_id"):
        return False
    if event.get("subtype") in ("message_changed", "message_deleted"):
        return False
    if event.get("type") != "message":
        return False
    if event.get("subtype") is not None:
        return False
    return True


@router.get("/install")
def slack_install(
    current_user: User = Depends(get_current_user_dependency),
) -> RedirectResponse:
    """Redirect to Slack OAuth; state = org_id. Returns 503 if Slack not configured."""
    if not settings.slack_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Slack is not configured. Set SLACK_CLIENT_ID (and related env vars) in .env.",
        )
    url = slack_service.start_oauth(current_user.org_id)
    return RedirectResponse(url=url, status_code=302)


@router.get("/install-url")
def slack_install_url(
    current_user: User = Depends(get_current_user_dependency),
) -> dict:
    """Return Slack OAuth URL in JSON so the SPA can set window.location (avoids CORS on redirect)."""
    if not settings.slack_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Slack is not configured. Set SLACK_CLIENT_ID (and related env vars) in .env.",
        )
    url = slack_service.start_oauth(current_user.org_id)
    return {"data": {"url": url}}


@router.get("/oauth/callback")
def slack_oauth_callback(
    db: Session = Depends(get_db),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """Handle Slack OAuth callback; no JWT. state = org_id."""
    if error:
        redirect = f"{settings.frontend_url}/settings?slack_error={error}"
        return RedirectResponse(url=redirect, status_code=302)
    if not code or not state:
        redirect = f"{settings.frontend_url}/settings?slack_error=missing_code"
        return RedirectResponse(url=redirect, status_code=302)
    try:
        org_id = uuid.UUID(state)
    except ValueError:
        redirect = f"{settings.frontend_url}/settings?slack_error=invalid_state"
        return RedirectResponse(url=redirect, status_code=302)
    conn = slack_service.handle_oauth_callback(db, org_id, code)
    if not conn:
        redirect = f"{settings.frontend_url}/settings?slack_error=exchange_failed"
        return RedirectResponse(url=redirect, status_code=302)
    redirect = f"{settings.frontend_url}/settings?slack_connected=1"
    return RedirectResponse(url=redirect, status_code=302)


@router.get("/channels")
def slack_channels(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """List Slack channels for the connected workspace."""
    channels = slack_service.get_channels(db, current_user.org_id)
    return {"data": [SlackChannelResponse(id=c["id"], name=c["name"]) for c in channels]}


@router.post("/channels")
def slack_set_channels(
    body: SlackChannelSelectRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Set monitored channel IDs."""
    conn = slack_service.set_monitored_channels(db, current_user.org_id, body.channel_ids)
    if not conn:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slack not connected.")
    return {"data": {"channels": conn.incoming_channels or []}}


@router.post("/events")
async def slack_events(request: Request) -> dict:
    """
    Slack Events API webhook. Verify signing; handle URL verification challenge;
    GAP 2: skip bot_id, message_changed/message_deleted; only type==message, no subtype.
    Enqueue process_slack_event and return 200 quickly.
    """
    body = await request.body()
    sig = request.headers.get("x-slack-signature")
    if not _verify_slack_signature(body, sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    import json
    payload = json.loads(body)
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge", "")}

    event = payload.get("event") or {}
    team_id = payload.get("team_id")
    if not team_id:
        return {}

    # Resolve org_id from team_id
    from app.database import SessionLocal
    from app.models.slack_connection import SlackConnection
    db = SessionLocal()
    try:
        conn = db.query(SlackConnection).filter(
            SlackConnection.team_id == team_id,
            SlackConnection.is_active == True,
        ).first()
        if not conn:
            return {}
        org_id = str(conn.org_id)
    finally:
        db.close()

    # GAP 2: only enqueue if it's a new user message
    if not _should_enqueue_message(event):
        return {}

    process_slack_event.delay(org_id, event)
    return {}


@router.get("/status")
def slack_status(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Return connection status and monitored channels."""
    status_data = slack_service.get_connection_status(db, current_user.org_id)
    return {"data": SlackConnectionStatusResponse(**status_data)}


@router.delete("/disconnect")
def slack_disconnect(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Disconnect Slack for this org."""
    ok = slack_service.disconnect(db, current_user.org_id)
    return {"data": {"disconnected": ok}}
