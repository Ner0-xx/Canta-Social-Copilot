import asyncio
import logging
import os
import shutil
import uuid
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    AppSettings,
    ContentDraft,
    ContentIdea,
    ContentPillar,
    OAuthConnection,
    PlatformPublication,
    PostMetric,
    SourceItem,
)
from app.policy import ActionType, PolicyContext, ReleaseLevel, evaluate_action
from app.routers.strategy import get_strategy
from app.schemas import (
    ContentDraftCreate,
    ContentDraftData,
    ContentIdeaCreate,
    ContentIdeaData,
    ContentStatusUpdate,
    DraftUpdateRequest,
)
from app.services.audit import record_audit_event
from app.services.draft_image import DraftImageError
from app.services.linkedin import LinkedInService
from app.services.llm import LLMService
from app.services.quality import evaluate_draft_quality
from app.services.x_oauth import XCredentialError, get_valid_x_access_token
from app.services.x_service import XAPIError, XService
from app.supabase_client import get_supabase

router = APIRouter(prefix="/content", tags=["content"])
llm_service = LLMService()
logger = logging.getLogger(__name__)

VALID_STATUSES = {"idea", "draft", "in_review", "approved", "scheduled", "published", "rejected"}


def _validate_status(status: str) -> str:
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Unsupported workflow status")
    return status


class GenerateIdeasRequest(BaseModel):
    source_item_id: int | None = None
    topic_title: str = Field(default="")
    topic_content: str = Field(default="")


class QualityCheckResponse(BaseModel):
    score: float
    warnings: list[str]


@router.post("/ideas", response_model=ContentIdeaData)
def create_idea(payload: ContentIdeaCreate, session: Session = Depends(get_db)) -> ContentIdea:
    idea = ContentIdea(
        title=payload.title,
        summary=payload.summary,
        source_type=payload.source_type,
        source_ref=payload.source_ref,
        pillar_id=payload.pillar_id,
        audience_id=payload.audience_id,
        relevance_score=payload.relevance_score,
        proposed_angle=payload.proposed_angle,
    )
    session.add(idea)
    record_audit_event(
        session,
        event_type="content.idea.created",
        entity_type="content_idea",
        entity_id=str(idea.id),
        summary="Idea created",
        details={"title": idea.title},
    )
    session.commit()
    session.refresh(idea)
    return idea


@router.get("/ideas", response_model=list[ContentIdeaData])
def list_ideas(session: Session = Depends(get_db)) -> list[ContentIdea]:
    return list(
        session.scalars(
            select(ContentIdea).order_by(ContentIdea.created_at.desc(), ContentIdea.id.desc())
        ).all()
    )


@router.post("/ideas/generate", response_model=list[ContentIdeaData])
async def generate_ideas_from_source(
    payload: GenerateIdeasRequest, session: Session = Depends(get_db)
) -> list[ContentIdea]:
    title = payload.topic_title
    content = payload.topic_content

    if payload.source_item_id:
        item = session.get(SourceItem, payload.source_item_id)
        if item:
            title = item.title
            content = item.content

    if not title and not content:
        raise HTTPException(status_code=400, detail="Provide source_item_id or topic_title/content")

    strategy = get_strategy(session)
    
    analytics_context = ""
    try:
        top_pillars = session.query(
            ContentIdea.pillar_id,
            func.sum(PostMetric.impressions).label('impressions')
        ).select_from(PostMetric).join(
            PlatformPublication, PostMetric.platform_post_id == PlatformPublication.platform_post_id
        ).join(
            ContentDraft, PlatformPublication.draft_id == ContentDraft.id
        ).join(
            ContentIdea, ContentDraft.idea_id == ContentIdea.id
        ).group_by(ContentIdea.pillar_id).order_by(desc('impressions')).limit(2).all()
        
        if top_pillars:
            pillar_ids = [p[0] for p in top_pillars]
            top_pillar_names = [p.name for p in session.query(ContentPillar).filter(ContentPillar.id.in_(pillar_ids)).all()]
            analytics_context = f"Based on recent analytics, your best performing content pillars are: {', '.join(top_pillar_names)}. Tailor ideas towards these successful areas if possible."
    except Exception as e:
        logger.warning(f"Could not fetch analytics context: {e}")

    generated = await llm_service.generate_ideas(title, content, strategy, analytics_context)

    created_ideas: list[ContentIdea] = []
    for data in generated:
        idea = ContentIdea(
            title=data.get("title", f"Idea from {title}"),
            summary=data.get("summary", ""),
            proposed_angle=data.get("proposed_angle", ""),
            relevance_score=float(data.get("relevance_score", 85.0)),
            source_type="generated",
            source_ref=title[:100],
            pillar_id=data.get("pillar_id"),
            audience_id=data.get("audience_id"),
            status="idea",
        )
        session.add(idea)
        created_ideas.append(idea)

    record_audit_event(
        session,
        event_type="content.ideas.generated",
        entity_type="content_idea",
        entity_id="batch",
        summary="Generated content ideas using AI service",
        details={"count": len(created_ideas), "source": title},
    )
    session.commit()
    for idea in created_ideas:
        session.refresh(idea)
    return created_ideas


@router.post("/ideas/{idea_id}/generate-drafts", response_model=list[ContentDraftData])
async def generate_drafts_for_idea(
    idea_id: int, session: Session = Depends(get_db)
) -> list[ContentDraft]:
    idea = session.get(ContentIdea, idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")

    strategy = get_strategy(session)
    draft_data = await llm_service.generate_draft_variants(
        idea.title, idea.summary, idea.proposed_angle, strategy
    )

    created_drafts: list[ContentDraft] = []

    # 1. X Single Post
    x_body = draft_data.get("x_post", "")
    qc_x = evaluate_draft_quality(x_body, "x", "post", strategy)
    x_draft = ContentDraft(
        idea_id=idea.id,
        platform="x",
        variant_type="post",
        title=f"X Post: {idea.title}",
        body=x_body,
        status="draft",
        quality_score=qc_x.score,
        warnings=qc_x.warnings,
    )
    session.add(x_draft)
    created_drafts.append(x_draft)

    # 2. X Thread
    x_thread_list = draft_data.get("x_thread", [])
    if isinstance(x_thread_list, list) and x_thread_list:
        thread_body = "\n\n---\n\n".join(x_thread_list)
        qc_thread = evaluate_draft_quality(thread_body, "x", "thread", strategy)
        thread_draft = ContentDraft(
            idea_id=idea.id,
            platform="x",
            variant_type="thread",
            title=f"X Thread: {idea.title}",
            body=thread_body,
            status="draft",
            quality_score=qc_thread.score,
            warnings=qc_thread.warnings,
        )
        session.add(thread_draft)
        created_drafts.append(thread_draft)

    # 3. LinkedIn Post
    li_body = draft_data.get("linkedin_post", "")
    qc_li = evaluate_draft_quality(li_body, "linkedin", "post", strategy)
    li_draft = ContentDraft(
        idea_id=idea.id,
        platform="linkedin",
        variant_type="post",
        title=f"LinkedIn: {idea.title}",
        body=li_body,
        status="draft",
        quality_score=qc_li.score,
        warnings=qc_li.warnings,
    )
    session.add(li_draft)
    created_drafts.append(li_draft)

    idea.status = "draft"
    record_audit_event(
        session,
        event_type="content.drafts.generated",
        entity_type="content_idea",
        entity_id=str(idea.id),
        summary="Auto-generated platform draft variants",
        details={"idea_id": idea.id, "count": len(created_drafts)},
    )
    session.commit()
    for d in created_drafts:
        session.refresh(d)
    return created_drafts


@router.get("/drafts", response_model=list[ContentDraftData])
def list_drafts(session: Session = Depends(get_db)) -> list[ContentDraft]:
    return list(
        session.scalars(
            select(ContentDraft).order_by(ContentDraft.created_at.desc(), ContentDraft.id.desc())
        ).all()
    )


@router.post("/ideas/{idea_id}/drafts", response_model=ContentDraftData)
def create_draft(
    idea_id: int, payload: ContentDraftCreate, session: Session = Depends(get_db)
) -> ContentDraft:
    idea = session.get(ContentIdea, idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")

    strategy = get_strategy(session)
    qc = evaluate_draft_quality(payload.body, payload.platform, payload.variant_type, strategy)

    draft = ContentDraft(
        idea_id=idea.id,
        platform=payload.platform,
        variant_type=payload.variant_type,
        title=payload.title,
        body=payload.body,
        image_path=payload.image_path,
        quality_score=qc.score,
        warnings=qc.warnings,
    )
    session.add(draft)
    record_audit_event(
        session,
        event_type="content.draft.created",
        entity_type="content_draft",
        entity_id=str(draft.id),
        summary="Draft created",
        details={"idea_id": idea.id, "platform": payload.platform},
    )
    session.commit()
    session.refresh(draft)
    return draft


@router.post("/drafts/{draft_id}/check", response_model=QualityCheckResponse)
def check_draft_quality(
    draft_id: int, session: Session = Depends(get_db)
) -> QualityCheckResponse:
    draft = session.get(ContentDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")

    strategy = get_strategy(session)
    qc = evaluate_draft_quality(draft.body, draft.platform, draft.variant_type, strategy)
    draft.quality_score = qc.score
    draft.warnings = qc.warnings
    session.commit()
    return QualityCheckResponse(score=qc.score, warnings=qc.warnings)


@router.post("/drafts/{draft_id}/transition", response_model=ContentDraftData)
def transition_draft(
    draft_id: int, payload: ContentStatusUpdate, session: Session = Depends(get_db)
) -> ContentDraft:
    draft = session.get(ContentDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")

    new_status = _validate_status(payload.status)

    # Invalidate approval if status is reverted or edited
    draft.status = new_status
    record_audit_event(
        session,
        event_type="content.draft.transitioned",
        entity_type="content_draft",
        entity_id=str(draft.id),
        summary="Draft status updated",
        details={"status": draft.status},
    )
    session.commit()
    session.refresh(draft)
    return draft


@router.put("/drafts/{draft_id}", response_model=ContentDraftData)
def update_draft(
    draft_id: int, payload: DraftUpdateRequest, session: Session = Depends(get_db)
) -> ContentDraft:
    draft = session.get(ContentDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")

    if payload.title is not None:
        draft.title = payload.title
    if payload.image_path is not None:
        draft.image_path = payload.image_path
    if payload.experiment_id is not None:
        draft.experiment_id = payload.experiment_id
    if payload.experiment_variant is not None:
        draft.experiment_variant = payload.experiment_variant
    if payload.body is not None:
        draft.body = payload.body
        
        # If the body changes, we should invalidate approval
        if draft.status in {"approved", "scheduled"}:
            draft.status = "draft"
            
    draft.version += 1

    record_audit_event(
        session,
        event_type="content.draft.updated",
        entity_type="content_draft",
        entity_id=str(draft.id),
        summary="Draft edited",
        details={"version": draft.version, "status": draft.status},
    )
    session.commit()
    session.refresh(draft)
    return draft


@router.post("/drafts/{draft_id}/image", response_model=ContentDraftData)
async def upload_draft_image(
    draft_id: int, file: UploadFile = File(...), session: Session = Depends(get_db)
) -> ContentDraft:
    draft = session.get(ContentDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")

    ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    
    supabase = get_supabase()
    if supabase:
        # Upload to Supabase Storage bucket 'images'
        file_bytes = await file.read()
        res = supabase.storage.from_("images").upload(
            path=filename, 
            file=file_bytes, 
            file_options={"content-type": file.content_type}
        )
        # Get public URL
        public_url = supabase.storage.from_("images").get_public_url(filename)
        draft.image_path = public_url
    else:
        os.makedirs("data/uploads", exist_ok=True)
        filepath = os.path.join("data/uploads", filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        draft.image_path = f"/uploads/{filename}"
    
    record_audit_event(
        session,
        event_type="content.draft.image_uploaded",
        entity_type="content_draft",
        entity_id=str(draft.id),
        summary="Draft image uploaded",
        details={"image_path": draft.image_path},
    )
    session.commit()
    session.refresh(draft)
    return draft


@router.post("/drafts/{draft_id}/publish-manual", response_model=ContentDraftData)
def publish_manual(
    draft_id: int, session: Annotated[Session, Depends(get_db)]
) -> ContentDraft:
    draft = session.get(ContentDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.status != "approved":
        raise HTTPException(
            status_code=400,
            detail="Only approved drafts can be published manually",
        )

    if draft.platform not in {"x", "linkedin"}:
        raise HTTPException(
            status_code=400,
            detail="Manual publishing is supported only for X and LinkedIn.",
        )

    settings = session.get(AppSettings, 1) or AppSettings(
        id=1, release_level="observe", publishing_enabled=False
    )
    connection = session.query(OAuthConnection).filter_by(platform=draft.platform).first()
    if not connection or not connection.encrypted_tokens:
        raise HTTPException(
            status_code=409,
            detail=f"Connect {draft.platform.capitalize()} in Settings first.",
        )
    decision = evaluate_action(
        ActionType.API_PUBLISH,
        PolicyContext(
            release_level=ReleaseLevel.parse(settings.release_level),
            publishing_enabled=settings.publishing_enabled,
            approved=True,
            official_api=True,
            explicit_user_request=True,
        ),
    )
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
    try:
        if draft.platform == "x":
            access_token = asyncio.run(get_valid_x_access_token(connection, session))
            platform_post_id = asyncio.run(
                XService().publish_post(access_token, draft.body, draft.image_path)
            )
        else:
            if not connection.encrypted_tokens:
                raise HTTPException(
                    status_code=409, detail="Connect LinkedIn in Settings first."
                )
            if connection.expires_at and connection.expires_at <= datetime.now(UTC).replace(
                tzinfo=None
            ):
                raise HTTPException(
                    status_code=401,
                    detail="LinkedIn access token expired. Reconnect LinkedIn.",
                )
            platform_post_id = asyncio.run(
                LinkedInService().publish_post(
                    connection.encrypted_tokens, draft.body, draft.image_path
                )
            )
    except XAPIError as exc:
        status_code = exc.status_code if exc.status_code in {401, 403, 429} else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code not in {401, 403, 429}:
            status_code = 502
        raise HTTPException(
            status_code=status_code,
            detail=f"{draft.platform.capitalize()} rejected the publish request.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach {draft.platform.capitalize()}. Try again shortly.",
        ) from exc
    except XCredentialError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except DraftImageError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=422,
            detail="The draft image could not be read. Re-upload it and try again.",
        ) from exc

    draft.status = "published"
    pub = PlatformPublication(
        draft_id=draft.id,
        platform=draft.platform,
        platform_post_id=platform_post_id,
        status="published",
    )
    session.add(pub)

    record_audit_event(
        session,
        event_type="content.draft.published",
        entity_type="content_draft",
        entity_id=str(draft.id),
        summary=f"Draft published to {draft.platform}",
        details={"platform": draft.platform, "post_id": platform_post_id},
    )
    session.commit()
    session.refresh(draft)
    return draft
