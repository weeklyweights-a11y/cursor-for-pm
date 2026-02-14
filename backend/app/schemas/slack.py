from pydantic import BaseModel, Field


class SlackChannelResponse(BaseModel):
    """Single Slack channel for selection."""

    id: str
    name: str


class SlackChannelSelectRequest(BaseModel):
    """Request body to set monitored channels."""

    channel_ids: list[str] = Field(..., min_length=0)


class SlackConnectionStatusResponse(BaseModel):
    """Slack connection status for settings page."""

    connected: bool
    team_name: str | None = None
    channels: list[str] = Field(default_factory=list)
