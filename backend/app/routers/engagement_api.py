import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.llm import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/engagement", tags=["engagement"])

# For MVP, we use an in-memory mock inbox since API fetching is restricted.
# In a real app, this would be a DB table populated by webhooks.
MOCK_INBOX = [
    {
        "id": "1",
        "platform": "linkedin",
        "author": "Alice Smith",
        "content": "This is a great perspective on AI! How do you think this affects smaller businesses?",
        "post_title": "The Future of Generative AI in Enterprise"
    },
    {
        "id": "2",
        "platform": "x",
        "author": "@tech_guru",
        "content": "Not sure I agree with the second point. Costs are still too high.",
        "post_title": "Why open source models will win"
    }
]

class DraftReplyRequest(BaseModel):
    comment_content: str
    post_title: str
    tone: str = "professional and helpful"

class DraftReplyResponse(BaseModel):
    draft_reply: str

@router.get("/inbox")
def get_inbox():
    return MOCK_INBOX

@router.post("/draft-reply", response_model=DraftReplyResponse)
def draft_reply(req: DraftReplyRequest):
    prompt = f"""
    You are an AI assistant helping a user manage their social media engagement.
    
    The user published a post titled: "{req.post_title}"
    Someone commented: "{req.comment_content}"
    
    Draft a {req.tone} reply to this comment. 
    Keep it concise, authentic, and suited for social media.
    Do not use hashtags.
    """
    
    try:
        llm = LLMService()
        # In a real scenario we'd use generate_text, which we have in LLMService
        response_text = llm.generate_text(prompt)
        return DraftReplyResponse(draft_reply=response_text)
    except Exception as e:
        logger.error(f"Failed to draft reply: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate reply from LLM.")
