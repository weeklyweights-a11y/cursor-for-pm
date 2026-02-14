"""
Slack OAuth and event processing. GAP 2: message filtering in process_slack_message.
GAP 3: OAuth scopes exactly channels:history, channels:read, users:read, users:read.email.
"""

from datetime import datetime, timezone
from uuid import UUID

from slack_sdk import WebClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models.slack_connection import SlackConnection
from app.services.encryption_service import decrypt, encrypt
from app.services.feedback_service import check_duplicate, create_feedback_item

# GAP 3: Exact OAuth scopes — no extra, no fewer.
SLACK_OAUTH_SCOPES = [
    "channels:history",
    "channels:read",
    "users:read",
    "users:read.email",
]


def _client(token: str | None = None) -> WebClient:
    return WebClient(token=token)


def start_oauth(org_id: UUID) -> str:
    """Build Slack OAuth authorize URL with state=org_id. Uses GAP 3 scopes."""
    base_url = settings.backend_url.rstrip("/")
    redirect_uri = f"{base_url}/api/v1/slack/oauth/callback"
    scopes = ",".join(SLACK_OAUTH_SCOPES)
    return (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={settings.slack_client_id}"
        f"&scope={scopes}"
        f"&redirect_uri={redirect_uri}"
        f"&state={org_id}"
    )


def handle_oauth_callback(db: Session, org_id: UUID, code: str) -> SlackConnection | None:
    """Exchange code for token, store encrypted, return SlackConnection."""
    client = _client()
    base_url = settings.backend_url.rstrip("/")
    redirect_uri = f"{base_url}/api/v1/slack/oauth/callback"
    response = client.oauth_v2_access(
        client_id=settings.slack_client_id,
        client_secret=settings.slack_client_secret,
        code=code,
        redirect_uri=redirect_uri,
    )
    if not response.get("ok"):
        return None
    team = response.get("team") or {}
    authed = response.get("authed_user") or response
    bot = response.get("bot") or {}
    access_token = (bot.get("access_token") or response.get("access_token") or "").strip()
    if not access_token:
        return None
    bot_user_id = (bot.get("bot_user_id") or response.get("bot_user_id") or "").strip()
    team_id = team.get("id") or response.get("team", {}).get("id") or ""
    team_name = team.get("name") or response.get("team", {}).get("name") or "Slack"

    existing = db.query(SlackConnection).filter(SlackConnection.org_id == org_id).first()
    encrypted_token = encrypt(access_token)
    if existing:
        existing.team_id = team_id
        existing.team_name = team_name
        existing.access_token = encrypted_token
        existing.bot_user_id = bot_user_id or existing.bot_user_id
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing
    conn = SlackConnection(
        org_id=org_id,
        team_id=team_id,
        team_name=team_name,
        access_token=encrypted_token,
        bot_user_id=bot_user_id or None,
        incoming_channels=None,
        is_active=True,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


def get_connection(db: Session, org_id: UUID) -> SlackConnection | None:
    """Get active Slack connection for org."""
    return (
        db.query(SlackConnection)
        .filter(SlackConnection.org_id == org_id, SlackConnection.is_active == True)
        .first()
    )


def get_channels(db: Session, org_id: UUID) -> list[dict]:
    """List public channels for the connected workspace."""
    conn = get_connection(db, org_id)
    if not conn:
        return []
    token = decrypt(conn.access_token)
    client = _client(token)
    channels = []
    cursor = None
    while True:
        resp = client.conversations_list(
            types="public_channel",
            exclude_archived=True,
            limit=200,
            cursor=cursor,
        )
        if not resp.get("ok"):
            break
        channels.extend(resp.get("channels") or [])
        cursor = (resp.get("response_metadata") or {}).get("next_cursor")
        if not cursor:
            break
    return [{"id": c["id"], "name": c.get("name", "")} for c in channels]


def set_monitored_channels(db: Session, org_id: UUID, channel_ids: list[str]) -> SlackConnection | None:
    """Update incoming_channels and join each channel."""
    conn = get_connection(db, org_id)
    if not conn:
        return None
    token = decrypt(conn.access_token)
    client = _client(token)
    for ch_id in channel_ids:
        try:
            client.conversations_join(channel=ch_id)
        except Exception:
            pass
    conn.incoming_channels = channel_ids
    db.commit()
    db.refresh(conn)
    return conn


def get_connection_status(db: Session, org_id: UUID) -> dict:
    """Return connection status and monitored channels."""
    conn = get_connection(db, org_id)
    if not conn:
        return {"connected": False, "team_name": None, "channels": []}
    return {
        "connected": True,
        "team_name": conn.team_name,
        "channels": list(conn.incoming_channels or []),
    }


def disconnect(db: Session, org_id: UUID) -> bool:
    """Deactivate Slack connection for org."""
    conn = get_connection(db, org_id)
    if not conn:
        return False
    conn.is_active = False
    conn.access_token = ""
    db.commit()
    return True


# GAP 2: Skip bot messages, message_changed/message_deleted; process only type==message with no subtype.
def _should_process_event(event: dict) -> bool:
    if event.get("bot_id"):
        return False
    if event.get("subtype") in ("message_changed", "message_deleted"):
        return False
    if event.get("type") != "message":
        return False
    if event.get("subtype") is not None:
        return False
    return True


def process_slack_message(
    db: Session,
    org_id: UUID,
    event_data: dict,
):
    """
    Process one Slack message event. Applies GAP 2 filters. Uses source_id = channel_id:message_ts.
    Checks duplicate (GAP 5) before creating. Returns created FeedbackItem or None if skipped.
    """
    if not _should_process_event(event_data):
        return None

    channel_id = event_data.get("channel") or ""
    ts = event_data.get("ts") or ""
    user_id = event_data.get("user") or ""
    text = (event_data.get("text") or "").strip()
    if not channel_id or not ts or not text:
        return None

    source_id = f"{channel_id}:{ts}"
    conn = get_connection(db, org_id)
    if not conn:
        return None
    if conn.incoming_channels and channel_id not in conn.incoming_channels:
        return None
    if check_duplicate(db, org_id, source_id):
        return None

    token = decrypt(conn.access_token)
    client = _client(token)
    author_email: str | None = None
    author_name: str | None = None
    try:
        user_resp = client.users_info(user=user_id)
        if user_resp.get("ok") and user_resp.get("user"):
            profile = (user_resp["user"].get("profile") or {})
            author_email = profile.get("email") or None
            author_name = (profile.get("real_name") or user_resp["user"].get("name") or "").strip() or None
    except Exception:
        pass

    try:
        ts_float = float(ts)
        timestamp = datetime.fromtimestamp(ts_float, tz=timezone.utc)
    except (TypeError, ValueError):
        timestamp = None

    metadata_: dict = {"channel_id": channel_id, "team_id": conn.team_id}
    try:
        ch = client.conversations_info(channel=channel_id)
        if ch.get("ok") and ch.get("channel"):
            metadata_["channel_name"] = ch["channel"].get("name")
    except Exception:
        pass
    if event_data.get("thread_ts"):
        metadata_["thread_ts"] = event_data["thread_ts"]

    item = create_feedback_item(
        db,
        org_id,
        content=text,
        source_type="slack",
        source_id=source_id,
        timestamp=timestamp,
        author_email=author_email,
        author_name=author_name,
        metadata_=metadata_,
    )
    return item
