import csv
import io
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db import get_db
from app.models import MetricImport, PostMetric, PlatformPublication, ContentDraft, ContentIdea, ContentPillar, AudienceSegment, AABExperiment, WeeklyReport
from app.schemas import AABExperimentCreate, AABExperimentData, WeeklyReportData
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

class ManualMetricEntry(BaseModel):
    platform_post_id: str
    platform: str
    impressions: int = 0
    reactions: int = 0
    comments: int = 0
    reposts: int = 0
    clicks: int = 0

class AnalyticsDashboardResponse(BaseModel):
    total_impressions: int
    total_reactions: int
    top_posts: List[dict]
    pillar_performance: List[dict]

@router.post("/import/csv")
async def import_csv_metrics(
    platform: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_db)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    
    metric_import = MetricImport(filename=file.filename, source_platform=platform)
    session.add(metric_import)
    session.flush()
    
    record_count = 0
    for row in reader:
        # Generic mapping strategy (handles LinkedIn exports loosely)
        # LinkedIn usually has: "Post link", "Impressions", "Reactions", "Comments", "Reposts", "Clicks"
        link = row.get("Post link", row.get("Post URL", f"import_{metric_import.id}_{record_count}"))
        
        # Extract ID from link if possible, else use the link itself as a proxy for platform_post_id
        platform_post_id = link.split("urn:li:share:")[-1] if "urn:li:share:" in link else link
        
        try:
            impressions = int(row.get("Impressions", 0).replace(",", ""))
            reactions = int(row.get("Reactions", row.get("Likes", 0)).replace(",", ""))
            comments = int(row.get("Comments", 0).replace(",", ""))
            reposts = int(row.get("Reposts", row.get("Shares", 0)).replace(",", ""))
            clicks = int(row.get("Clicks", 0).replace(",", ""))
        except Exception:
            continue # Skip rows that don't have parsable numbers
            
        metric = PostMetric(
            import_id=metric_import.id,
            platform=platform,
            platform_post_id=platform_post_id,
            impressions=impressions,
            reactions=reactions,
            comments=comments,
            reposts=reposts,
            clicks=clicks
        )
        session.add(metric)
        record_count += 1
        
    metric_import.record_count = record_count
    session.commit()
    
    return {"message": f"Successfully imported {record_count} records", "import_id": metric_import.id}

@router.post("/import/manual")
def import_manual_metrics(entries: List[ManualMetricEntry], session: Session = Depends(get_db)):
    count = 0
    for entry in entries:
        # Check if exists, update or create
        existing = session.query(PostMetric).filter_by(
            platform=entry.platform, 
            platform_post_id=entry.platform_post_id
        ).first()
        
        if existing:
            existing.impressions = entry.impressions
            existing.reactions = entry.reactions
            existing.comments = entry.comments
            existing.reposts = entry.reposts
            existing.clicks = entry.clicks
        else:
            metric = PostMetric(
                platform=entry.platform,
                platform_post_id=entry.platform_post_id,
                impressions=entry.impressions,
                reactions=entry.reactions,
                comments=entry.comments,
                reposts=entry.reposts,
                clicks=entry.clicks
            )
            session.add(metric)
        count += 1
        
    session.commit()
    return {"message": f"Successfully logged {count} manual entries"}

@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
def get_dashboard_metrics(session: Session = Depends(get_db)):
    # Total aggregates
    totals = session.query(
        func.sum(PostMetric.impressions).label("impressions"),
        func.sum(PostMetric.reactions).label("reactions")
    ).first()
    
    # Top Posts
    top_posts_query = session.query(
        PostMetric,
        PlatformPublication
    ).outerjoin(
        PlatformPublication, 
        PostMetric.platform_post_id == PlatformPublication.platform_post_id
    ).order_by(desc(PostMetric.impressions)).limit(5).all()
    
    top_posts = []
    for metric, pub in top_posts_query:
        title = "Unknown Post (Imported)"
        if pub:
            draft = session.query(ContentDraft).filter_by(id=pub.draft_id).first()
            if draft:
                title = draft.title
                
        top_posts.append({
            "platform_post_id": metric.platform_post_id,
            "platform": metric.platform,
            "title": title,
            "impressions": metric.impressions,
            "reactions": metric.reactions
        })
        
    # Pillar performance (join Draft -> Idea -> Pillar)
    # This requires more complex joins
    # For MVP, we fetch all and calculate in Python
    pillars = session.query(ContentPillar).all()
    pillar_data = {}
    for p in pillars:
        pillar_data[p.id] = {"name": p.name, "impressions": 0, "reactions": 0}
        
    # Map metrics to pillars via publication
    pubs = session.query(PlatformPublication, ContentDraft, ContentIdea).join(
        ContentDraft, PlatformPublication.draft_id == ContentDraft.id
    ).join(
        ContentIdea, ContentDraft.idea_id == ContentIdea.id
    ).all()
    
    pub_to_pillar = {pub.PlatformPublication.platform_post_id: pub.ContentIdea.pillar_id for pub in pubs}
    
    all_metrics = session.query(PostMetric).all()
    for m in all_metrics:
        p_id = pub_to_pillar.get(m.platform_post_id)
        if p_id and p_id in pillar_data:
            pillar_data[p_id]["impressions"] += m.impressions
            pillar_data[p_id]["reactions"] += m.reactions
            
    return AnalyticsDashboardResponse(
        total_impressions=totals.impressions or 0,
        total_reactions=totals.reactions or 0,
        top_posts=top_posts,
        pillar_performance=list(pillar_data.values())
    )

@router.get("/recent-publications")
def get_recent_publications(platform: Optional[str] = None, session: Session = Depends(get_db)):
    """Fetch recent publications to populate the manual entry grid."""
    query = session.query(PlatformPublication, ContentDraft).join(
        ContentDraft, PlatformPublication.draft_id == ContentDraft.id
    )
    if platform:
        query = query.filter(PlatformPublication.platform == platform)
        
    results = query.order_by(desc(PlatformPublication.published_at)).limit(20).all()
    
    response = []
    for pub, draft in results:
        # Check if metric already exists
        metric = session.query(PostMetric).filter_by(platform_post_id=pub.platform_post_id).first()
        
        response.append({
            "platform_post_id": pub.platform_post_id,
            "platform": pub.platform,
            "title": draft.title,
            "published_at": pub.published_at,
            "metrics": {
                "impressions": metric.impressions if metric else 0,
                "reactions": metric.reactions if metric else 0,
                "comments": metric.comments if metric else 0,
                "reposts": metric.reposts if metric else 0
            }
        })
    return response

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

@router.get("/experiments", response_model=List[AABExperimentData])
def get_experiments(session: Session = Depends(get_db)):
    experiments = session.query(AABExperiment).order_by(desc(AABExperiment.created_at)).all()
    results = []
    
    for exp in experiments:
        exp_data = AABExperimentData.model_validate(exp)
        
        # Calculate metrics for each variant
        variant_metrics = {}
        drafts = session.query(ContentDraft).filter_by(experiment_id=exp.id).all()
        for d in drafts:
            if not d.experiment_variant:
                continue
            if d.experiment_variant not in variant_metrics:
                variant_metrics[d.experiment_variant] = {"impressions": 0, "reactions": 0, "posts": 0}
                
            pubs = session.query(PlatformPublication).filter_by(draft_id=d.id).all()
            for pub in pubs:
                metric = session.query(PostMetric).filter_by(platform_post_id=pub.platform_post_id).first()
                if metric:
                    variant_metrics[d.experiment_variant]["impressions"] += metric.impressions
                    variant_metrics[d.experiment_variant]["reactions"] += metric.reactions
            variant_metrics[d.experiment_variant]["posts"] += 1
            
        exp_data.metrics = variant_metrics
        results.append(exp_data)
        
    return results

@router.get("/reports", response_model=List[WeeklyReportData])
def get_weekly_reports(session: Session = Depends(get_db)):
    return session.query(WeeklyReport).order_by(desc(WeeklyReport.week_start)).all()
