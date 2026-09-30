from datetime import datetime, timedelta
import logging
import json

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import SessionLocal
from app.models import WeeklyReport, PostMetric
from app.services.llm import LLMService

logger = logging.getLogger(__name__)

def generate_weekly_report():
    logger.info("Starting weekly performance report generation...")
    
    with SessionLocal() as session:
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        
        # Aggregate metrics
        totals = session.query(
            func.sum(PostMetric.impressions).label("impressions"),
            func.sum(PostMetric.reactions).label("reactions")
        ).filter(PostMetric.imported_at >= start_time).first()
        
        impressions = totals.impressions or 0
        reactions = totals.reactions or 0
        
        # Get top post by impressions
        top_post = session.query(PostMetric).filter(
            PostMetric.imported_at >= start_time
        ).order_by(PostMetric.impressions.desc()).first()
        top_post_id = top_post.platform_post_id if top_post else None
        
        # Generate insights using LLM
        prompt = f"""
        You are a social media performance analyst. 
        Analyze the following metrics for the past 7 days and provide a 2-3 sentence insight on performance and 1 concrete recommendation for next week.
        
        Metrics:
        Total Impressions: {impressions}
        Total Reactions: {reactions}
        Top Post ID (if any): {top_post_id}
        """
        
        llm = LLMService()
        try:
            insights = llm.generate_idea(prompt)
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            insights = "Not enough data to generate insights for this week."
            
        report = WeeklyReport(
            week_start=start_time,
            week_end=end_time,
            total_impressions=impressions,
            total_reactions=reactions,
            top_pillar_id=None, # Simplifying for MVP
            top_post_id=top_post_id,
            insights_text=insights
        )
        
        session.add(report)
        session.commit()
        logger.info(f"Weekly report generated: ID {report.id}")
