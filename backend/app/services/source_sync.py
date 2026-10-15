import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Source, SourceItem
from app.services.audit import record_audit_event
from app.services.ingestion import IngestionService

logger = logging.getLogger(__name__)
ingestion_service = IngestionService()


async def sync_source_items(session: Session, source: Source) -> list[SourceItem]:
    try:
        extracted_items = await ingestion_service.process_source(source)

        for item_data in extracted_items:
            existing = session.scalar(
                select(SourceItem).where(
                    SourceItem.content_hash == item_data["content_hash"]
                )
            )
            if existing:
                continue
            session.add(
                SourceItem(
                    source_id=source.id,
                    title=item_data["title"],
                    author=item_data["author"],
                    url=item_data["url"],
                    canonical_url=item_data["canonical_url"],
                    content=item_data["content"],
                    content_hash=item_data["content_hash"],
                    published_at=item_data["published_at"],
                )
            )

        source.last_fetched_at = datetime.now(UTC).replace(tzinfo=None)
        source.status = "active"
        record_audit_event(
            session,
            event_type="source.synced",
            entity_type="source",
            entity_id=str(source.id),
            summary="Source items synced",
            details={"items_processed": len(extracted_items)},
        )
        session.commit()
    except Exception:
        session.rollback()
        failed_source = session.get(Source, source.id)
        if failed_source is not None:
            failed_source.status = "error"
            session.commit()
        raise

    return list(
        session.scalars(
            select(SourceItem)
            .where(SourceItem.source_id == source.id)
            .order_by(SourceItem.ingested_at.desc(), SourceItem.id.desc())
        ).all()
    )


async def sync_all_active_sources() -> None:
    logger.info("Starting scheduled source synchronization")
    with SessionLocal() as session:
        source_ids = session.scalars(
            select(Source.id)
            .where(Source.status.in_(("active", "error")))
            .order_by(Source.id)
        ).all()

        for source_id in source_ids:
            source = session.get(Source, source_id)
            if source is None:
                continue
            try:
                items = await sync_source_items(session, source)
                logger.info(
                    "Scheduled sync completed for source %s (%s items available)",
                    source.id,
                    len(items),
                )
            except Exception:
                logger.exception("Scheduled sync failed for source %s", source_id)

    logger.info("Finished scheduled source synchronization")
