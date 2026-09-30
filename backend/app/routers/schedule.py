from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.db import get_db
from app.models import ScheduledJob, ContentDraft
from app.schemas import ScheduledJobCreate, ScheduledJobData
from app.services.audit import record_audit_event
from app.scheduler import scheduler
from app.services.scheduler_job import process_scheduled_job

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/", response_model=list[ScheduledJobData])
def list_scheduled_jobs(session: Session = Depends(get_db)):
    return list(
        session.scalars(
            select(ScheduledJob).order_by(ScheduledJob.scheduled_at.asc())
        ).all()
    )


@router.post("/", response_model=ScheduledJobData)
def create_scheduled_job(payload: ScheduledJobCreate, session: Session = Depends(get_db)):
    draft = session.get(ContentDraft, payload.draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.status != "approved":
        raise HTTPException(status_code=400, detail="Only approved drafts can be scheduled")

    # Add to DB
    job = ScheduledJob(
        draft_id=draft.id,
        platform=payload.platform,
        scheduled_at=payload.scheduled_at,
        status="pending"
    )
    session.add(job)
    draft.status = "scheduled"
    
    session.commit()
    session.refresh(job)

    record_audit_event(
        session,
        event_type="content.job.scheduled",
        entity_type="scheduled_job",
        entity_id=str(job.id),
        summary=f"Draft scheduled for {payload.scheduled_at}",
        details={"draft_id": draft.id, "platform": payload.platform}
    )
    session.commit()

    # Add to APScheduler
    # Make sure we pass the correct date to APScheduler. APScheduler expects datetime.
    # If the datetime is naive, APScheduler will assume local time.
    run_date = payload.scheduled_at
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=timezone.utc)
        
    scheduler.add_job(
        process_scheduled_job,
        "date",
        run_date=run_date,
        args=[job.id],
        id=f"job_{job.id}",
        replace_existing=True
    )

    return job


@router.delete("/{job_id}")
def cancel_scheduled_job(job_id: int, session: Session = Depends(get_db)):
    job = session.get(ScheduledJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    if job.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending jobs can be cancelled")

    job.status = "cancelled"
    
    draft = session.get(ContentDraft, job.draft_id)
    if draft and draft.status == "scheduled":
        draft.status = "approved"

    record_audit_event(
        session,
        event_type="content.job.cancelled",
        entity_type="scheduled_job",
        entity_id=str(job.id),
        summary="Scheduled job cancelled by user",
        details={"draft_id": job.draft_id}
    )
    session.commit()

    # Remove from APScheduler if it exists
    try:
        scheduler.remove_job(f"job_{job.id}")
    except Exception:
        pass # Job might not exist in the APScheduler memory store

    return {"message": "Job cancelled"}
