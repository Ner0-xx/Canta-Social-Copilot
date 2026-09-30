import logging
from app.db import SessionLocal
from app.services.publisher import PublisherService

logger = logging.getLogger(__name__)

def process_scheduled_job(job_id: int):
    logger.info(f"APScheduler triggered for job {job_id}")
    session = SessionLocal()
    try:
        publisher = PublisherService()
        publisher.execute_scheduled_job(job_id, session)
    except Exception as e:
        logger.error(f"Error executing scheduled job {job_id}: {e}")
    finally:
        session.close()
