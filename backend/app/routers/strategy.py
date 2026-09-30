from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AudienceSegment, BrandProfile, ContentPillar, VoiceProfile
from app.schemas import (
    AudienceSegmentData,
    BrandProfileData,
    ContentPillarData,
    StrategyData,
    VoiceProfileData,
)
from app.services.audit import record_audit_event

router = APIRouter(prefix="/strategy", tags=["strategy"])


def _get_or_create(session: Session, model: type[BrandProfile] | type[VoiceProfile]):
    instance = session.get(model, 1)
    if instance is None:
        instance = model(id=1)
        session.add(instance)
        session.flush()
    return instance


@router.get("", response_model=StrategyData)
def get_strategy(session: Session = Depends(get_db)) -> StrategyData:
    brand = _get_or_create(session, BrandProfile)
    voice = _get_or_create(session, VoiceProfile)
    audiences = session.scalars(
        select(AudienceSegment).order_by(AudienceSegment.position, AudienceSegment.id)
    ).all()
    pillars = session.scalars(
        select(ContentPillar).order_by(ContentPillar.position, ContentPillar.id)
    ).all()
    session.commit()

    return StrategyData(
        brand=BrandProfileData(
            display_name=brand.display_name,
            account_purpose=brand.account_purpose,
            biography=brand.biography,
            expertise=brand.expertise,
            offers=brand.offers,
            business_goals=brand.business_goals,
            sensitive_topics=brand.sensitive_topics,
            required_disclosures=brand.required_disclosures,
        ),
        voice=VoiceProfileData(
            tone=voice.tone,
            preferred_vocabulary=voice.preferred_vocabulary,
            avoided_vocabulary=voice.avoided_vocabulary,
            formatting_preferences=voice.formatting_preferences,
            call_to_action_style=voice.call_to_action_style,
            writing_examples=voice.writing_examples,
        ),
        audiences=[
            AudienceSegmentData(
                id=item.id,
                name=item.name,
                description=item.description,
                needs=item.needs,
                interests=item.interests,
                desired_action=item.desired_action,
            )
            for item in audiences
        ],
        pillars=[
            ContentPillarData(
                id=item.id,
                name=item.name,
                description=item.description,
                target_percentage=item.target_percentage,
                example_topics=item.example_topics,
            )
            for item in pillars
        ],
    )


@router.put("", response_model=StrategyData)
def update_strategy(payload: StrategyData, session: Session = Depends(get_db)) -> StrategyData:
    brand = _get_or_create(session, BrandProfile)
    for field, value in payload.brand.model_dump().items():
        setattr(brand, field, value)

    voice = _get_or_create(session, VoiceProfile)
    for field, value in payload.voice.model_dump().items():
        setattr(voice, field, value)

    session.execute(delete(AudienceSegment))
    session.execute(delete(ContentPillar))

    for position, audience in enumerate(payload.audiences):
        session.add(
            AudienceSegment(
                name=audience.name,
                description=audience.description,
                needs=audience.needs,
                interests=audience.interests,
                desired_action=audience.desired_action,
                position=position,
            )
        )

    for position, pillar in enumerate(payload.pillars):
        session.add(
            ContentPillar(
                name=pillar.name,
                description=pillar.description,
                target_percentage=pillar.target_percentage,
                example_topics=pillar.example_topics,
                position=position,
            )
        )

    record_audit_event(
        session,
        event_type="strategy.updated",
        entity_type="strategy",
        entity_id="primary",
        summary="Strategy profile updated",
        details={
            "audience_count": len(payload.audiences),
            "pillar_count": len(payload.pillars),
            "writing_example_count": len(payload.voice.writing_examples),
        },
    )
    session.commit()
    return get_strategy(session)

