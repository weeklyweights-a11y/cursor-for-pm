"""Chat-related Celery tasks (Phase 6)."""

from pathlib import Path
from uuid import UUID

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.conversation import Conversation
from app.services.llm_chat import call_chat_llm
from app.utils.logging import get_logger

logger = get_logger(__name__)
_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "title_generation.txt"


@celery_app.task(bind=True)
def auto_title_task(self, conversation_id: str, first_message: str) -> None:
    """Generate a short title from the first message and set conversation.title. On failure, leave title null."""
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(Conversation.id == UUID(conversation_id)).first()
        if not conv:
            logger.warning("auto_title_task: conversation not found", extra={"conversation_id": conversation_id})
            return
        prompt = _PROMPT_PATH.read_text().strip()
        messages = [{"role": "user", "content": (first_message or "")[:1000]}]
        title_text, _ = call_chat_llm(prompt, messages, tools=None)
        title = (title_text or "").strip()[:255]
        if title:
            conv.title = title
            db.commit()
            logger.info("auto_title_task: title set", extra={"conversation_id": conversation_id})
        else:
            conv.title = "New conversation"
            db.commit()
    except Exception as e:
        logger.error("auto_title_task failed", extra={"conversation_id": conversation_id, "error": str(e)})
    finally:
        db.close()
