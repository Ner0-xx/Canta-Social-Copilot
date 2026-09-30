from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import get_settings
from app.db import Base, engine
from app.routers import content, health, settings as settings_router, sources, strategy, schedule, oauth, analytics_api, engagement_api
from app.scheduler import scheduler
from app.services.weekly_report import generate_weekly_report
from app.auth import verify_jwt
from fastapi import Depends

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    
    # Register weekly report job (e.g. run every Monday at 00:00)
    scheduler.add_job(
        generate_weekly_report,
        "cron",
        day_of_week="mon",
        hour=0,
        minute=0,
        id="weekly_performance_report",
        replace_existing=True
    )
    
    scheduler.start()
    yield
    scheduler.shutdown()

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

os.makedirs("data/uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="data/uploads"), name="uploads")

app.include_router(health.router, prefix="/api")
app.include_router(oauth.router, prefix="/api")

# Protected Routes
app.include_router(content.router, prefix="/api", dependencies=[Depends(verify_jwt)])
app.include_router(sources.router, prefix="/api", dependencies=[Depends(verify_jwt)])
app.include_router(strategy.router, prefix="/api", dependencies=[Depends(verify_jwt)])
app.include_router(settings_router.router, prefix="/api", dependencies=[Depends(verify_jwt)])
app.include_router(schedule.router, prefix="/api", dependencies=[Depends(verify_jwt)])
app.include_router(analytics_api.router, prefix="/api", dependencies=[Depends(verify_jwt)])
app.include_router(engagement_api.router, prefix="/api", dependencies=[Depends(verify_jwt)])
