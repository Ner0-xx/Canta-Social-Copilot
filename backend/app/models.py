from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    release_level: Mapped[str] = mapped_column(String(32), default="observe")
    publishing_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    display_name: Mapped[str] = mapped_column(String(120), default="")
    account_purpose: Mapped[str] = mapped_column(Text, default="")
    biography: Mapped[str] = mapped_column(Text, default="")
    expertise: Mapped[list[str]] = mapped_column(JSON, default=list)
    offers: Mapped[list[str]] = mapped_column(JSON, default=list)
    business_goals: Mapped[list[str]] = mapped_column(JSON, default=list)
    sensitive_topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    required_disclosures: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class VoiceProfile(Base):
    __tablename__ = "voice_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    tone: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_vocabulary: Mapped[list[str]] = mapped_column(JSON, default=list)
    avoided_vocabulary: Mapped[list[str]] = mapped_column(JSON, default=list)
    formatting_preferences: Mapped[str] = mapped_column(Text, default="")
    call_to_action_style: Mapped[str] = mapped_column(Text, default="")
    writing_examples: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class AudienceSegment(Base):
    __tablename__ = "audience_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    needs: Mapped[list[str]] = mapped_column(JSON, default=list)
    interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    desired_action: Mapped[str] = mapped_column(String(240), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)


class ContentPillar(Base):
    __tablename__ = "content_pillars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    target_percentage: Mapped[float] = mapped_column(Float, default=0)
    example_topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    position: Mapped[int] = mapped_column(Integer, default=0)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), default="")
    entity_id: Mapped[str] = mapped_column(String(80), default="")
    summary: Mapped[str] = mapped_column(String(500))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class PlatformActionRecord(Base):
    __tablename__ = "platform_action_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(32))
    action_type: Mapped[str] = mapped_column(String(64))
    content_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id"), nullable=True)
    policy_decision: Mapped[str] = mapped_column(String(32))
    policy_reason: Mapped[str] = mapped_column(String(500))
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    source_type: Mapped[str] = mapped_column(String(40), default="note", index=True)
    uri_or_content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class SourceItem(Base):
    __tablename__ = "source_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    author: Mapped[str] = mapped_column(String(120), default="")
    url: Mapped[str] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    canonical_url: Mapped[str] = mapped_column(String(500), default="")
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ContentIdea(Base):
    __tablename__ = "content_ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="idea", index=True)
    source_type: Mapped[str] = mapped_column(String(40), default="")
    source_ref: Mapped[str] = mapped_column(String(500), default="")
    pillar_id: Mapped[int | None] = mapped_column(ForeignKey("content_pillars.id"), nullable=True)
    audience_id: Mapped[int | None] = mapped_column(ForeignKey("audience_segments.id"), nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    proposed_angle: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ContentDraft(Base):
    __tablename__ = "content_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("content_ideas.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), default="")
    variant_type: Mapped[str] = mapped_column(String(32), default="post")
    title: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    experiment_id: Mapped[int | None] = mapped_column(ForeignKey("aab_experiments.id"), nullable=True)
    experiment_variant: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    quality_score: Mapped[float] = mapped_column(Float, default=1.0)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    citations: Mapped[list[dict]] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    workflow_state: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("content_drafts.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(32))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    execution_log: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PlatformPublication(Base):
    __tablename__ = "platform_publications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("content_drafts.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(32))
    platform_post_id: Mapped[str] = mapped_column(String(120), default="")
    platform_post_url: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(32), default="published")
    published_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class OAuthConnection(Base):
    __tablename__ = "oauth_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    account_name: Mapped[str] = mapped_column(String(120), default="")
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    encrypted_tokens: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MetricImport(Base):
    __tablename__ = "metric_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(200))
    source_platform: Mapped[str] = mapped_column(String(32))
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PostMetric(Base):
    __tablename__ = "post_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int | None] = mapped_column(ForeignKey("metric_imports.id"), nullable=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    platform_post_id: Mapped[str] = mapped_column(String(120), index=True)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    reactions: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    reposts: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AABExperiment(Base):
    __tablename__ = "aab_experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    hypothesis: Mapped[str] = mapped_column(Text, default="")
    start_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_start: Mapped[datetime] = mapped_column(DateTime)
    week_end: Mapped[datetime] = mapped_column(DateTime)
    total_impressions: Mapped[int] = mapped_column(Integer, default=0)
    total_reactions: Mapped[int] = mapped_column(Integer, default=0)
    top_pillar_id: Mapped[int | None] = mapped_column(ForeignKey("content_pillars.id"), nullable=True)
    top_post_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    insights_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

