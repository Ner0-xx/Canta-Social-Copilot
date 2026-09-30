import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app.models import ScheduledJob, ContentDraft, PlatformActionRecord, PlatformPublication, AppSettings, OAuthConnection
from app.policy import evaluate_action, ActionType, PolicyContext, ReleaseLevel
import asyncio
from app.services.linkedin import LinkedInService
from app.services.x_service import XService
from app.services.audit import record_audit_event

logger = logging.getLogger(__name__)

class PublisherService:
    def execute_scheduled_job(self, job_id: int, session: Session) -> None:
        job = session.get(ScheduledJob, job_id)
        if not job or job.status != "pending":
            logger.info(f"Job {job_id} is not pending or does not exist.")
            return

        draft = session.get(ContentDraft, job.draft_id)
        if not draft:
            self._fail_job(job, session, "Draft not found.")
            return

        settings = session.get(AppSettings, 1) or AppSettings()
        release_level = ReleaseLevel.parse(settings.release_level)

        context = PolicyContext(
            release_level=release_level,
            publishing_enabled=settings.publishing_enabled,
            approved=True if draft.status == "scheduled" else False,
            official_api=True, # Will be true when Phase 4 connects OAuth
            explicit_user_request=False
        )

        decision = evaluate_action(ActionType.API_PUBLISH, context)
        if not decision.allowed:
            self._fail_job(job, session, f"Policy block: {decision.reason}")
            return

        idempotency_key = f"publish_job_{job.id}_v{draft.version}"
        
        try:
            record = PlatformActionRecord(
                platform=job.platform,
                action_type="api_publish",
                content_id=None,
                policy_decision="allowed",
                policy_reason=decision.reason,
                idempotency_key=idempotency_key
            )
            session.add(record)
            session.flush() # Check for integrity error immediately
        except IntegrityError:
            session.rollback()
            logger.warning(f"Idempotency key {idempotency_key} already exists. Skipping.")
            return
            
        try:
            platform_post_id = None
            if job.platform in ["linkedin", "x"]:
                conn = session.query(OAuthConnection).filter_by(platform=job.platform).first()
                if not conn or not conn.encrypted_tokens:
                    raise Exception(f"No active {job.platform} connection found.")
                
                if conn.expires_at and conn.expires_at < datetime.now():
                    raise Exception(f"{job.platform} token expired.")
                
                if job.platform == "linkedin":
                    svc = LinkedInService()
                    platform_post_id = asyncio.run(
                        svc.publish_post(conn.encrypted_tokens, draft.body, draft.image_path)
                    )
                elif job.platform == "x":
                    svc = XService()
                    platform_post_id = asyncio.run(
                        svc.publish_post(conn.encrypted_tokens, draft.body, draft.image_path)
                    )
                    
                logger.info(f"Published draft {draft.id} to {job.platform}: {platform_post_id}")
            else:
                # MOCK PUBLISHING for other platforms
                logger.info(f"Mock publishing draft {draft.id} to {job.platform}")
                platform_post_id = f"mock_{job.platform}_{int(datetime.now().timestamp())}"
            
            pub = PlatformPublication(
                draft_id=draft.id,
                platform=job.platform,
                platform_post_id=platform_post_id,
                status="published"
            )
            session.add(pub)
            
            draft.status = "published"
            job.status = "completed"
            job.execution_log = {"success": True, "post_id": platform_post_id}
            
            record_audit_event(
                session,
                event_type="content.job.executed",
                entity_type="scheduled_job",
                entity_id=str(job.id),
                summary=f"Successfully published to {job.platform}",
                details={"post_id": platform_post_id}
            )
            session.commit()
            
        except Exception as e:
            session.rollback()
            self._fail_job(job, session, f"API Error: {str(e)}")

    def _fail_job(self, job: ScheduledJob, session: Session, reason: str):
        job.status = "failed"
        job.execution_log = {"success": False, "error": reason}
        
        draft = session.get(ContentDraft, job.draft_id)
        if draft:
            draft.status = "approved" # Revert so they can try again
            
        record_audit_event(
            session,
            event_type="content.job.failed",
            entity_type="scheduled_job",
            entity_id=str(job.id),
            summary=f"Job failed: {reason}",
            details={"error": reason}
        )
        session.commit()
