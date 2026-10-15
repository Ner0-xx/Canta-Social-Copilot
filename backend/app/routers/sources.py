from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Source, SourceItem
from app.schemas import SourceCreate, SourceData, SourceItemData
from app.services.audit import record_audit_event
from app.services.source_sync import sync_source_items

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("", response_model=SourceData)
async def create_source(payload: SourceCreate, session: Session = Depends(get_db)) -> Source:
    source = Source(
        name=payload.name or payload.source_type.title(),
        source_type=payload.source_type,
        uri_or_content=payload.uri_or_content,
        status="active",
    )
    session.add(source)
    session.flush()

    record_audit_event(
        session,
        event_type="source.created",
        entity_type="source",
        entity_id=str(source.id),
        summary="Source added",
        details={"name": source.name, "type": source.source_type},
    )
    session.commit()
    session.refresh(source)

    # Immediately attempt ingestion
    await sync_source(source.id, session)
    session.refresh(source)
    return source


@router.get("", response_model=list[SourceData])
def list_sources(session: Session = Depends(get_db)) -> list[Source]:
    return list(
        session.scalars(select(Source).order_by(Source.created_at.desc(), Source.id.desc())).all()
    )


@router.get("/items", response_model=list[SourceItemData])
def list_source_items(session: Session = Depends(get_db)) -> list[SourceItem]:
    return list(
        session.scalars(
            select(SourceItem).order_by(SourceItem.ingested_at.desc(), SourceItem.id.desc())
        ).all()
    )


@router.post("/{source_id}/sync", response_model=list[SourceItemData])
async def sync_source(source_id: int, session: Session = Depends(get_db)) -> list[SourceItem]:
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        return await sync_source_items(session, source)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Source processing failed: {exc}",
        ) from exc


@router.delete("/{source_id}")
def delete_source(source_id: int, session: Session = Depends(get_db)) -> dict[str, int | str]:
    source = session.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    source_name = source.name
    deleted_items = session.execute(
        delete(SourceItem).where(SourceItem.source_id == source_id)
    ).rowcount or 0
    session.delete(source)
    record_audit_event(
        session,
        event_type="source.deleted",
        entity_type="source",
        entity_id=str(source_id),
        summary="Source deleted",
        details={"name": source_name, "deleted_items": deleted_items},
    )
    session.commit()
    return {
        "message": "Source and its ingested items were deleted.",
        "deleted_items": deleted_items,
    }
