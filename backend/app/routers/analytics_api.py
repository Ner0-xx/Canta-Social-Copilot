import logging
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    AABExperiment,
    ContentDraft,
    ContentIdea,
    ContentPillar,
    PlatformPublication,
    PublicationMetricSnapshot,
    WeeklyReport,
)
from app.schemas import (
    AABExperimentCreate,
    AABExperimentData,
    MetricCheckpoint,
    PublicationMetricSnapshotData,
    PublicationMetricsUpdate,
    PublishedPublicationData,
    PublishedPublicationsPage,
    WeeklyReportData,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

class AnalyticsDashboardResponse(BaseModel):
    total_impressions: int
    total_reactions: int
    top_posts: list[dict]
    pillar_performance: list[dict]

CHECKPOINT_AGES = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}


def _publication_data(
    publication: PlatformPublication,
    draft: ContentDraft,
    snapshots: list[PublicationMetricSnapshot],
) -> PublishedPublicationData:
    return PublishedPublicationData(
        publication_id=publication.id,
        draft_id=draft.id,
        platform=publication.platform,
        platform_post_id=publication.platform_post_id,
        platform_post_url=publication.platform_post_url,
        title=draft.title,
        published_at=publication.published_at,
        metrics={
            snapshot.checkpoint: PublicationMetricSnapshotData.model_validate(snapshot)
            for snapshot in snapshots
        },
    )


@router.get("/publications", response_model=PublishedPublicationsPage)
def get_published_publications(
    platform: Literal["x", "linkedin"],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str = Query(default="", max_length=120),
    session: Session = Depends(get_db),
) -> PublishedPublicationsPage:
    query = (
        select(PlatformPublication, ContentDraft)
        .join(ContentDraft, PlatformPublication.draft_id == ContentDraft.id)
        .where(
            PlatformPublication.platform == platform,
            PlatformPublication.status.in_(("published", "manual_confirmed")),
        )
    )
    if search.strip():
        query = query.where(ContentDraft.title.ilike(f"%{search.strip()}%"))

    total = session.scalar(
        select(func.count())
        .select_from(query.subquery())
    ) or 0
    results = session.execute(
        query.order_by(
            PlatformPublication.published_at.desc(),
            PlatformPublication.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()
    publication_ids = [publication.id for publication, _draft in results]
    snapshots = session.scalars(
        select(PublicationMetricSnapshot)
        .where(PublicationMetricSnapshot.publication_id.in_(publication_ids))
        .order_by(PublicationMetricSnapshot.checkpoint)
    ).all() if publication_ids else []
    snapshots_by_publication: dict[int, list[PublicationMetricSnapshot]] = {}
    for snapshot in snapshots:
        snapshots_by_publication.setdefault(snapshot.publication_id, []).append(snapshot)

    return PublishedPublicationsPage(
        items=[
            _publication_data(
                publication,
                draft,
                snapshots_by_publication.get(publication.id, []),
            )
            for publication, draft in results
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.put(
    "/publications/{publication_id}/metrics",
    response_model=PublicationMetricSnapshotData,
)
def save_publication_metrics(
    publication_id: int,
    payload: PublicationMetricsUpdate,
    session: Session = Depends(get_db),
) -> PublicationMetricSnapshot:
    publication = session.get(PlatformPublication, publication_id)
    if publication is None or publication.status not in {
        "published",
        "manual_confirmed",
    }:
        raise HTTPException(status_code=404, detail="Published post not found")

    now = datetime.now(UTC).replace(tzinfo=None)
    published_at = publication.published_at
    if published_at.tzinfo is not None:
        published_at = published_at.astimezone(UTC).replace(tzinfo=None)
    age = max(timedelta(0), now - published_at)
    checkpoint: MetricCheckpoint = (
        "90d" if age > CHECKPOINT_AGES["90d"] else payload.checkpoint
    )
    is_late = age > CHECKPOINT_AGES[checkpoint]

    snapshot = session.scalar(
        select(PublicationMetricSnapshot).where(
            PublicationMetricSnapshot.publication_id == publication.id,
            PublicationMetricSnapshot.checkpoint == checkpoint,
        )
    )
    if snapshot is None:
        snapshot = PublicationMetricSnapshot(
            publication_id=publication.id,
            checkpoint=checkpoint,
        )
        session.add(snapshot)

    for field in ("impressions", "reactions", "comments", "reposts", "clicks"):
        setattr(snapshot, field, getattr(payload, field))
    snapshot.recorded_at = now
    snapshot.is_late = is_late
    session.commit()
    session.refresh(snapshot)
    return snapshot

@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
def get_dashboard_metrics(
    checkpoint: MetricCheckpoint = "7d",
    platform: Literal["all", "x", "linkedin"] = "all",
    session: Session = Depends(get_db),
):
    query = (
        select(
            PublicationMetricSnapshot,
            PlatformPublication,
            ContentDraft,
            ContentIdea,
            ContentPillar,
        )
        .join(
            PlatformPublication,
            PublicationMetricSnapshot.publication_id == PlatformPublication.id,
        )
        .join(ContentDraft, PlatformPublication.draft_id == ContentDraft.id)
        .join(ContentIdea, ContentDraft.idea_id == ContentIdea.id)
        .outerjoin(ContentPillar, ContentIdea.pillar_id == ContentPillar.id)
        .where(
            PublicationMetricSnapshot.checkpoint == checkpoint,
            PlatformPublication.status.in_(("published", "manual_confirmed")),
        )
    )
    if platform != "all":
        query = query.where(PlatformPublication.platform == platform)

    rows = session.execute(query).all()
    total_impressions = sum(metric.impressions for metric, *_ in rows)
    total_reactions = sum(metric.reactions for metric, *_ in rows)

    top_posts = [
        {
            "platform_post_id": publication.platform_post_id,
            "platform": publication.platform,
            "title": draft.title,
            "impressions": metric.impressions,
            "reactions": metric.reactions,
        }
        for metric, publication, draft, _idea, _pillar in sorted(
            rows, key=lambda row: row[0].impressions, reverse=True
        )[:5]
    ]

    pillar_data: dict[int, dict] = {}
    for metric, _publication, _draft, idea, pillar in rows:
        if idea.pillar_id is None or pillar is None:
            continue
        values = pillar_data.setdefault(
            idea.pillar_id,
            {"name": pillar.name, "impressions": 0, "reactions": 0},
        )
        values["impressions"] += metric.impressions
        values["reactions"] += metric.reactions

    return AnalyticsDashboardResponse(
        total_impressions=total_impressions,
        total_reactions=total_reactions,
        top_posts=top_posts,
        pillar_performance=list(pillar_data.values()),
    )

@router.post("/experiments", response_model=AABExperimentData)
def create_experiment(payload: AABExperimentCreate, session: Session = Depends(get_db)):
    exp = AABExperiment(
        name=payload.name,
        hypothesis=payload.hypothesis,
        end_date=payload.end_date
    )
    session.add(exp)
    session.commit()
    session.refresh(exp)
    return exp

@router.get("/experiments", response_model=list[AABExperimentData])
def get_experiments(session: Session = Depends(get_db)):
    experiments = session.query(AABExperiment).order_by(desc(AABExperiment.created_at)).all()
    results = []
    
    for exp in experiments:
        exp_data = AABExperimentData.model_validate(exp)
        
        variant_metrics = {}
        drafts = session.query(ContentDraft).filter_by(experiment_id=exp.id).all()
        for d in drafts:
            if not d.experiment_variant:
                continue
            pubs = session.query(PlatformPublication).filter_by(draft_id=d.id).all()
            for pub in pubs:
                metric = session.scalar(
                    select(PublicationMetricSnapshot).where(
                        PublicationMetricSnapshot.publication_id == pub.id,
                        PublicationMetricSnapshot.checkpoint == "7d",
                    )
                )
                if not metric:
                    continue
                variant = f"{d.experiment_variant} · {pub.platform}"
                values = variant_metrics.setdefault(
                    variant, {"impressions": 0, "reactions": 0, "posts": 0}
                )
                values["impressions"] += metric.impressions
                values["reactions"] += metric.reactions
                values["posts"] += 1
            
        exp_data.metrics = variant_metrics
        results.append(exp_data)
        
    return results

@router.get("/reports", response_model=list[WeeklyReportData])
def get_weekly_reports(session: Session = Depends(get_db)):
    return session.query(WeeklyReport).order_by(desc(WeeklyReport.week_start)).all()
