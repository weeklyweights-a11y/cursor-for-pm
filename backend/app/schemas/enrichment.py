from pydantic import BaseModel


class ReEnrichResponse(BaseModel):
    """Response after queuing re-enrichment for unmatched items."""

    items_queued: int = 0
