def test_create_and_list_ideas(client) -> None:
    response = client.post(
        "/api/content/ideas",
        json={
            "title": "Launch a practical leadership thread",
            "summary": "A short idea about leading with calm under pressure.",
            "source_type": "rss",
            "source_ref": "https://example.com/leadership",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "idea"
    assert payload["title"] == "Launch a practical leadership thread"

    listing = client.get("/api/content/ideas")
    assert listing.status_code == 200
    assert any(item["id"] == payload["id"] for item in listing.json())


def test_create_draft_and_transition_status(client) -> None:
    idea = client.post(
        "/api/content/ideas",
        json={
            "title": "Share a weekly systems tip",
            "summary": "A short idea for a recurring content series.",
            "source_type": "note",
            "source_ref": "personal-note",
        },
    ).json()

    draft = client.post(
        f"/api/content/ideas/{idea['id']}/drafts",
        json={
            "platform": "x",
            "title": "Weekly systems tip",
            "body": "Small systems make big teams calmer.",
        },
    )

    assert draft.status_code == 200
    draft_payload = draft.json()
    assert draft_payload["status"] == "draft"

    transition = client.post(
        f"/api/content/drafts/{draft_payload['id']}/transition",
        json={"status": "approved"},
    )

    assert transition.status_code == 200
    assert transition.json()["status"] == "approved"


def test_publication_checkpoint_metrics_are_upserted_and_late_posts_use_90d(client):
    from datetime import datetime, timedelta

    from app.db import get_db
    from app.models import ContentDraft, ContentIdea, PlatformPublication, PublicationMetricSnapshot

    generator = client.app.dependency_overrides[get_db]()
    session = next(generator)
    idea = ContentIdea(title="Analytics checkpoint", summary="A published post.")
    session.add(idea)
    session.flush()
    draft = ContentDraft(
        idea_id=idea.id,
        platform="linkedin",
        title="LinkedIn checkpoint post",
        body="Post text.",
        status="published",
    )
    session.add(draft)
    session.flush()
    publication = PlatformPublication(
        draft_id=draft.id,
        platform="linkedin",
        platform_post_id="urn:li:share:checkpoint-1",
        platform_post_url="https://www.linkedin.com/feed/update/urn:li:share:checkpoint-1",
        published_at=datetime.now() - timedelta(days=100),
    )
    session.add(publication)
    session.commit()
    publication_id = publication.id
    generator.close()

    first = client.put(
        f"/api/analytics/publications/{publication_id}/metrics",
        json={
            "checkpoint": "24h",
            "impressions": 1000,
            "reactions": 20,
            "comments": 4,
            "reposts": 3,
            "clicks": 7,
        },
    )
    assert first.status_code == 200
    assert first.json()["checkpoint"] == "90d"
    assert first.json()["is_late"] is True
    assert first.json()["impressions"] == 1000

    second = client.put(
        f"/api/analytics/publications/{publication_id}/metrics",
        json={
            "checkpoint": "7d",
            "impressions": 1200,
            "reactions": 30,
            "comments": 5,
            "reposts": 4,
            "clicks": 8,
        },
    )
    assert second.status_code == 200
    assert second.json()["checkpoint"] == "90d"
    assert second.json()["impressions"] == 1200

    generator = client.app.dependency_overrides[get_db]()
    session = next(generator)
    assert (
        session.query(PublicationMetricSnapshot)
        .filter_by(publication_id=publication_id)
        .count()
        == 1
    )
    generator.close()

    listed = client.get("/api/analytics/publications?platform=linkedin&search=checkpoint")
    assert listed.status_code == 200
    page = listed.json()
    assert page["total"] == 1
    assert page["items"][0]["metrics"]["90d"]["impressions"] == 1200
    assert "24h" not in page["items"][0]["metrics"]
    assert client.post("/api/analytics/import/csv").status_code == 404
