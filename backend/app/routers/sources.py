from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Source, SourceItem
from app.schemas import SourceCreate, SourceData, SourceItemData
from app.services.audit import record_audit_event
from app.services.ingestion import IngestionService

router = APIRouter(prefix="/sources", tags=["sources"])
ingestion_service = IngestionService()


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
        extracted_items = await ingestion_service.process_source(source)
        created_items: list[SourceItem] = []

        for item_data in extracted_items:
            # Check deduplication hash
            existing = session.scalar(
                select(SourceItem).where(SourceItem.content_hash == item_data["content_hash"])
            )
            if not existing:
                item = SourceItem(
                    source_id=source.id,
                    title=item_data["title"],
                    author=item_data["author"],
                    url=item_data["url"],
                    canonical_url=item_data["canonical_url"],
                    content=item_data["content"],
                    content_hash=item_data["content_hash"],
                    published_at=item_data["published_at"],
                )
                session.add(item)
                created_items.append(item)

        source.last_fetched_at = source.created_at
        source.status = "active"

        record_audit_event(
            session,
            event_type="source.synced",
            entity_type="source",
            entity_id=str(source.id),
            summary="Source items synced",
            details={"new_items": len(created_items)},
        )
        session.commit()

        return list(
            session.scalars(
                select(SourceItem)
                .where(SourceItem.source_id == source.id)
                .order_by(SourceItem.ingested_at.desc())
            ).all()
        )
    except Exception as exc:
        source.status = "error"
        session.commit()
        raise HTTPException(status_code=400, detail=f"Source processing failed: {exc}")
