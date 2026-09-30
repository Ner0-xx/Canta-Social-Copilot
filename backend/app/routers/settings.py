from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AppSettings, AuditEvent
from app.policy import ActionType, PolicyContext, ReleaseLevel, evaluate_action
from app.schemas import (
    AppSettingsData,
    AppSettingsUpdate,
    AuditEventData,
    PolicyEvaluationRequest,
    PolicyEvaluationResponse,
)
from app.services.audit import record_audit_event

router = APIRouter(tags=["settings"])


def get_or_create_settings(session: Session) -> AppSettings:
    settings = session.get(AppSettings, 1)
    if settings is None:
        settings = AppSettings(id=1, release_level="observe", publishing_enabled=False)
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


@router.get("/settings", response_model=AppSettingsData)
def read_settings(session: Session = Depends(get_db)) -> AppSettings:
    return get_or_create_settings(session)


@router.put("/settings", response_model=AppSettingsData)
def update_settings(
    payload: AppSettingsUpdate, session: Session = Depends(get_db)
) -> AppSettings:
    try:
        ReleaseLevel.parse(payload.release_level)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    settings = get_or_create_settings(session)
    previous_level = settings.release_level
    previous_enabled = settings.publishing_enabled
    settings.release_level = payload.release_level.lower()
    settings.publishing_enabled = payload.publishing_enabled
    record_audit_event(
        session,
        event_type="settings.updated",
        entity_type="app_settings",
        entity_id="1",
        summary="Release controls updated",
        details={
            "previous_release_level": previous_level,
            "release_level": settings.release_level,
            "previous_publishing_enabled": previous_enabled,
            "publishing_enabled": settings.publishing_enabled,
        },
    )
    session.commit()
    session.refresh(settings)
    return settings


@router.post("/policy/evaluate", response_model=PolicyEvaluationResponse)
def evaluate_policy(
    payload: PolicyEvaluationRequest, session: Session = Depends(get_db)
) -> PolicyEvaluationResponse:
    settings = get_or_create_settings(session)
    try:
        action = ActionType(payload.action)
        release_level = ReleaseLevel.parse(settings.release_level)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    decision = evaluate_action(
        action,
        PolicyContext(
            release_level=release_level,
            publishing_enabled=settings.publishing_enabled,
            approved=payload.approved,
            official_api=payload.official_api,
            explicit_user_request=payload.explicit_user_request,
        ),
    )
    return PolicyEvaluationResponse(
        allowed=decision.allowed,
        reason=decision.reason,
        required_release_level=(
            decision.required_release_level.name.lower()
            if decision.required_release_level
            else None
        ),
    )


@router.get("/audit-events", response_model=list[AuditEventData])
def list_audit_events(
    limit: int = 50, session: Session = Depends(get_db)
) -> list[AuditEvent]:
    safe_limit = max(1, min(limit, 200))
    return list(
        session.scalars(
            select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(
                safe_limit
            )
        )
    )

