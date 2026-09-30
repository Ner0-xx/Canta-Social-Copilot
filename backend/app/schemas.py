from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class BrandProfileData(BaseModel):
    display_name: str = Field(default="", max_length=120)
    account_purpose: str = Field(default="", max_length=2000)
    biography: str = Field(default="", max_length=4000)
    expertise: list[str] = Field(default_factory=list, max_length=30)
    offers: list[str] = Field(default_factory=list, max_length=30)
    business_goals: list[str] = Field(default_factory=list, max_length=30)
    sensitive_topics: list[str] = Field(default_factory=list, max_length=30)
    required_disclosures: list[str] = Field(default_factory=list, max_length=30)


class VoiceProfileData(BaseModel):
    tone: list[str] = Field(default_factory=list, max_length=20)
    preferred_vocabulary: list[str] = Field(default_factory=list, max_length=50)
    avoided_vocabulary: list[str] = Field(default_factory=list, max_length=50)
    formatting_preferences: str = Field(default="", max_length=2000)
    call_to_action_style: str = Field(default="", max_length=1000)
    writing_examples: list[str] = Field(default_factory=list, max_length=20)


class AudienceSegmentData(BaseModel):
    id: int | None = None
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    needs: list[str] = Field(default_factory=list, max_length=30)
    interests: list[str] = Field(default_factory=list, max_length=30)
    desired_action: str = Field(default="", max_length=240)


class ContentPillarData(BaseModel):
    id: int | None = None
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    target_percentage: float = Field(default=0, ge=0, le=100)
    example_topics: list[str] = Field(default_factory=list, max_length=30)


class StrategyData(BaseModel):
    brand: BrandProfileData = Field(default_factory=BrandProfileData)
    voice: VoiceProfileData = Field(default_factory=VoiceProfileData)
    audiences: list[AudienceSegmentData] = Field(default_factory=list, max_length=12)
    pillars: list[ContentPillarData] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_pillar_total(self) -> "StrategyData":
        total = sum(pillar.target_percentage for pillar in self.pillars)
        if self.pillars and abs(total - 100) > 0.01:
            raise ValueError("Content pillar percentages must add up to 100")
        return self


class AppSettingsData(BaseModel):
    release_level: str
    publishing_enabled: bool


class AppSettingsUpdate(BaseModel):
    release_level: str
    publishing_enabled: bool


class PolicyEvaluationRequest(BaseModel):
    action: str
    platform: str
    approved: bool = False
    official_api: bool = False
    explicit_user_request: bool = False


class PolicyEvaluationResponse(BaseModel):
    allowed: bool
    reason: str
    required_release_level: str | None = None


class SourceCreate(BaseModel):
    name: str = Field(default="", max_length=120)
    source_type: str = Field(default="note", max_length=40)
    uri_or_content: str = Field(min_length=1, max_length=50000)


class SourceData(BaseModel):
    id: int
    name: str
    source_type: str
    uri_or_content: str
    status: str
    last_fetched_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SourceItemData(BaseModel):
    id: int
    source_id: int | None = None
    title: str
    author: str
    url: str
    content: str
    canonical_url: str
    content_hash: str
    published_at: datetime | None = None
    ingested_at: datetime

    model_config = {"from_attributes": True}


class ContentIdeaCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(default="", max_length=4000)
    source_type: str = Field(default="", max_length=40)
    source_ref: str = Field(default="", max_length=500)
    pillar_id: int | None = None
    audience_id: int | None = None
    relevance_score: float = Field(default=0.0, ge=0.0, le=100.0)
    proposed_angle: str = Field(default="", max_length=1000)


class ContentIdeaData(BaseModel):
    id: int
    title: str
    summary: str
    status: str
    source_type: str
    source_ref: str
    pillar_id: int | None = None
    audience_id: int | None = None
    relevance_score: float = 0.0
    proposed_angle: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentDraftCreate(BaseModel):
    platform: str = Field(default="", max_length=32)
    variant_type: str = Field(default="post", max_length=32)
    title: str = Field(default="", max_length=200)
    body: str = Field(default="", max_length=12000)
    image_path: str | None = Field(default=None, max_length=500)


class DraftUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=12000)
    image_path: str | None = Field(default=None, max_length=500)
    experiment_id: int | None = None
    experiment_variant: str | None = Field(default=None, max_length=32)


class ContentDraftData(BaseModel):
    id: int
    idea_id: int
    platform: str
    variant_type: str = "post"
    title: str
    body: str
    image_path: str | None = None
    experiment_id: int | None = None
    experiment_variant: str | None = None
    status: str
    quality_score: float = 1.0
    warnings: list[str] = Field(default_factory=list)
    citations: list[dict] = Field(default_factory=list)
    version: int = 1
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=32)


class AuditEventData(BaseModel):
    id: int
    event_type: str
    entity_type: str
    entity_id: str
    summary: str
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class ScheduledJobCreate(BaseModel):
    draft_id: int
    platform: str = Field(min_length=1, max_length=32)
    scheduled_at: datetime


class ScheduledJobData(BaseModel):
    id: int
    draft_id: int
    platform: str
    scheduled_at: datetime
    status: str
    execution_log: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class PlatformPublicationData(BaseModel):
    id: int
    draft_id: int
    platform: str
    platform_post_id: str
    platform_post_url: str
    status: str
    published_at: datetime

    model_config = {"from_attributes": True}


class OAuthConnectionData(BaseModel):
    id: int
    platform: str
    account_name: str
    scopes: list[str]
    expires_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PostMetricData(BaseModel):
    id: int
    platform: str
    platform_post_id: str
    impressions: int
    reactions: int
    comments: int
    reposts: int
    clicks: int
    imported_at: datetime

    model_config = {"from_attributes": True}

class JobStatusResponse(BaseModel):
    id: int
    draft_id: int
    platform: str
    scheduled_at: datetime
    status: str
    execution_log: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AABExperimentCreate(BaseModel):
    name: str = Field(..., max_length=200)
    hypothesis: str = Field(default="")
    end_date: datetime | None = None


class AABExperimentData(BaseModel):
    id: int
    name: str
    hypothesis: str
    start_date: datetime
    end_date: datetime | None
    status: str
    created_at: datetime
    metrics: dict | None = None  # Populated dynamically for API response

    model_config = {"from_attributes": True}


class WeeklyReportData(BaseModel):
    id: int
    week_start: datetime
    week_end: datetime
    total_impressions: int
    total_reactions: int
    top_pillar_id: int | None
    top_post_id: str | None
    insights_text: str
    created_at: datetime

    model_config = {"from_attributes": True}

