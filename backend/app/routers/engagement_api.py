import logging
from collections import defaultdict
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import OAuthConnection
from app.services.llm import LLMService
from app.services.x_oauth import get_valid_x_access_token
from app.services.x_service import XAPIError, XService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/engagement", tags=["engagement"])

class DraftReplyRequest(BaseModel):
    comment_content: str
    post_title: str
    tone: str = "professional and helpful"

class DraftReplyResponse(BaseModel):
    draft_reply: str

def _translate_x_error(exc: Exception) -> HTTPException:
    if isinstance(exc, XAPIError):
        status_code = exc.status_code if exc.status_code in {401, 403, 429} else 502
        return HTTPException(status_code=status_code, detail=str(exc))
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code in {401, 403, 429}:
            return HTTPException(
                status_code=status_code,
                detail=(
                    "X denied the request. Reauthorize the account and confirm the app "
                    "has the required API access."
                ),
            )
        return HTTPException(status_code=502, detail="X API request failed.")
    if isinstance(exc, httpx.RequestError):
        return HTTPException(
            status_code=502,
            detail="Could not reach the X API. Try again shortly.",
        )
    if isinstance(exc, ValueError):
        return HTTPException(status_code=401, detail=str(exc))
    raise exc


async def _get_x_connection(session: Session) -> tuple[OAuthConnection, str]:
    connection = session.query(OAuthConnection).filter_by(platform="x").first()
    if not connection:
        raise HTTPException(status_code=409, detail="Connect an X account in Settings first.")
    try:
        return connection, await get_valid_x_access_token(connection, session)
    except (ValueError, XAPIError, httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise _translate_x_error(exc) from exc


@router.get("/x")
async def get_x_engagement(
    session: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=20, ge=5, le=100),
):
    connection, access_token = await _get_x_connection(session)
    service = XService()
    try:
        profile = await service.get_current_user(access_token)
        user_id = profile.get("id")
        if not user_id:
            raise HTTPException(
                status_code=502,
                detail="X did not return the connected account ID.",
            )
        posts, mentions = await service.get_recent_posts_and_mentions(
            access_token, user_id, limit
        )
    except (XAPIError, httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise _translate_x_error(exc) from exc

    username = profile.get("username", connection.account_name)

    def post_url(post: dict) -> str:
        return f"https://x.com/{username}/status/{post['id']}" if post.get("id") else ""

    return {
        "account": {
            "id": user_id,
            "name": profile.get("name", username),
            "username": username,
        },
        "posts": [
            {**post, "url": post_url(post)}
            for post in posts
            if isinstance(post, dict)
        ],
        "mentions": [
            {
                **mention,
                "url": (
                    f"https://x.com/{mention.get('author', {}).get('username', '')}"
                    f"/status/{mention['id']}"
                )
                if mention.get("id")
                else "",
            }
            for mention in mentions
        ],
    }


@router.get("/x/direct-messages")
async def get_x_direct_messages(session: Annotated[Session, Depends(get_db)]):
    _, access_token = await _get_x_connection(session)
    service = XService()
    try:
        profile = await service.get_current_user(access_token)
        response = await service.get_dm_events(access_token)
    except (XAPIError, httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise _translate_x_error(exc) from exc

    users = {
        user["id"]: user
        for user in response.get("includes", {}).get("users", [])
        if isinstance(user, dict) and user.get("id")
    }
    if profile.get("id"):
        users[profile["id"]] = profile
    grouped = defaultdict(list)
    for event in response.get("data", []):
        if not isinstance(event, dict) or not event.get("dm_conversation_id"):
            continue
        sender_id = event.get("sender_id", "")
        sender = users.get(sender_id, {})
        grouped[event["dm_conversation_id"]].append(
            {
                "id": event.get("id", ""),
                "sender_id": sender_id,
                "is_me": sender_id == profile.get("id"),
                "sender_name": sender.get("name", sender.get("username", "X user")),
                "sender_username": sender.get("username", ""),
                "text": event.get("text", ""),
                "created_at": event.get("created_at"),
            }
        )

    conversations = []
    for conversation_id, messages in grouped.items():
        messages.sort(key=lambda message: message.get("created_at") or "")
        latest = messages[-1]
        participant = next(
            (
                message
                for message in reversed(messages)
                if message["sender_id"] != profile.get("id")
            ),
            latest,
        )
        conversations.append(
            {
                "id": conversation_id,
                "participant": participant["sender_name"],
                "participant_username": participant["sender_username"],
                "messages": messages,
            }
        )
    conversations.sort(
        key=lambda conversation: conversation["messages"][-1].get("created_at") or "",
        reverse=True,
    )
    return {
        "account": {
            "name": profile.get("name", profile.get("username", "")),
            "username": profile.get("username", ""),
        },
        "conversations": conversations,
        "limited_to_recent_events": True,
    }

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
        raise HTTPException(
            status_code=500,
            detail="Failed to generate reply from LLM.",
        ) from e
