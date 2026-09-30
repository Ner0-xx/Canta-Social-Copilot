import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import (
    MetricImport,
    OAuthConnection,
    PlatformPublication,
    PostMetric,
    ScheduledJob,
    Source,
    SourceItem,
)
from app.schemas import (
    OAuthConnectionData,
    PlatformPublicationData,
    PostMetricData,
    ScheduledJobData,
    SourceCreate,
    SourceData,
    SourceItemData,
)


@pytest.fixture
def test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_source_and_source_item_models(test_session: Session):
    source = Source(
        name="AI Trends RSS",
        source_type="rss",
        uri_or_content="https://example.com/feed.xml",
    )
    test_session.add(source)
    test_session.commit()

    assert source.id is not None
    assert source.status == "active"

    item = SourceItem(
        source_id=source.id,
        title="New LLM Launch",
        author="Tech Desk",
        url="https://example.com/news/1",
        canonical_url="https://example.com/news/1",
        content_hash="abc123hash",
        content="Article content here",
    )
    test_session.add(item)
    test_session.commit()

    assert item.id is not None
    assert item.content_hash == "abc123hash"


def test_workflow_extended_models(test_session: Session):
    job = ScheduledJob(
        draft_id=1,
        platform="linkedin",
        scheduled_at=datetime.datetime.now(),
        status="pending",
    )
    test_session.add(job)

    pub = PlatformPublication(
        draft_id=1,
        platform="linkedin",
        platform_post_id="urn:li:share:123",
        platform_post_url="https://linkedin.com/feed/update/urn:li:share:123",
    )
    test_session.add(pub)

    oauth = OAuthConnection(
        platform="linkedin",
        account_name="User Profile",
        scopes=["w_member_social", "r_liteprofile"],
        encrypted_tokens="encrypted_data_blob",
    )
    test_session.add(oauth)

    metric_imp = MetricImport(
        filename="metrics_aug_2026.csv",
        source_platform="linkedin",
        record_count=15,
    )
    test_session.add(metric_imp)
    test_session.commit()

    metric = PostMetric(
        import_id=metric_imp.id,
        platform="linkedin",
        platform_post_id="urn:li:share:123",
        impressions=1250,
        reactions=45,
        comments=12,
        reposts=5,
        clicks=88,
    )
    test_session.add(metric)
    test_session.commit()

    assert job.id is not None
    assert pub.id is not None
    assert oauth.id is not None
    assert metric.id is not None
    assert metric.impressions == 1250


def test_source_schemas():
    source_create = SourceCreate(
        name="My Pasted Note",
        source_type="note",
        uri_or_content="Detailed content about new features.",
    )
    assert source_create.name == "My Pasted Note"
