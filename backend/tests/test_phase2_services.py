import asyncio
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.auth import verify_jwt
from app.db import get_db
from app.models import OAuthConnection
from app.services.ingestion import compute_content_hash
from app.services.llm import LLMService
from app.services.quality import evaluate_draft_quality


def test_content_hash_deduplication():
    hash1 = compute_content_hash("  Sample Text Content  ")
    hash2 = compute_content_hash("sample text content")
    assert hash1 == hash2


def test_llm_template_fallback():
    async def _test():
        llm = LLMService()
        ideas = await llm.generate_ideas("AI Trends 2026", "Content about recent advances in AI.")
        assert len(ideas) >= 3
        assert "title" in ideas[0]

        drafts = await llm.generate_draft_variants("AI Strategy", "How to use AI effectively.")
        assert "x_post" in drafts
        assert "x_thread" in drafts
        assert "linkedin_post" in drafts

    asyncio.run(_test())


def test_quality_evaluator():
    res_good = evaluate_draft_quality("Insightful post on AI productivity.", "x", "post")
    assert res_good.score == 1.0
    assert len(res_good.warnings) == 0

    long_body = "x" * 300
    res_long = evaluate_draft_quality(long_body, "x", "post")
    assert res_long.score < 1.0
    assert any("exceeds X 280-character limit" in w for w in res_long.warnings)


def test_sources_api(client: TestClient):
    resp = client.post(
        "/api/sources",
        json={
            "name": "My Tech Note",
            "source_type": "note",
            "uri_or_content": "This is a note about building localized AI copilot tools.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "My Tech Note"

    # List sources
    resp_list = client.get("/api/sources")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) >= 1

    # List source items
    resp_items = client.get("/api/sources/items")
    assert resp_items.status_code == 200
    assert len(resp_items.json()) >= 1


def test_idea_and_draft_generation_api(client: TestClient):
    # Generate ideas from topic
    gen_ideas_resp = client.post(
        "/api/content/ideas/generate",
        json={"topic_title": "Local LLMs in 2026", "topic_content": "Running LLMs on consumer hardware."},
    )
    assert gen_ideas_resp.status_code == 200
    ideas = gen_ideas_resp.json()
    assert len(ideas) >= 1
    idea_id = ideas[0]["id"]

    # Generate draft variants for idea
    gen_drafts_resp = client.post(f"/api/content/ideas/{idea_id}/generate-drafts")
    assert gen_drafts_resp.status_code == 200
    drafts = gen_drafts_resp.json()
    assert len(drafts) == 3

    # Check quality of draft
    draft_id = drafts[0]["id"]
    check_resp = client.post(f"/api/content/drafts/{draft_id}/check")
    assert check_resp.status_code == 200
    assert "score" in check_resp.json()


def test_disconnect_oauth_requires_auth_and_removes_connection(client: TestClient):
    session_generator = client.app.dependency_overrides[get_db]()
    session = next(session_generator)
    session.add(OAuthConnection(platform="x", account_name="example", encrypted_tokens="token"))
    session.commit()
    session_generator.close()

    auth_override = client.app.dependency_overrides.pop(verify_jwt)
    try:
        unauthorized = client.delete("/api/oauth/x")
        assert unauthorized.status_code == 401
    finally:
        client.app.dependency_overrides[verify_jwt] = auth_override

    try:
        response = client.delete("/api/oauth/x", headers={"Authorization": "Bearer test-token"})
        assert response.status_code == 200
        assert response.json() == {"disconnected": True, "platform": "x"}

        status_response = client.get("/api/oauth/x/status")
        assert status_response.status_code == 200
        assert status_response.json()["connected"] is False
    finally:
        client.app.dependency_overrides[verify_jwt] = auth_override


def test_oauth_status_keeps_saved_connection_visible_when_token_expires(client: TestClient):
    session_generator = client.app.dependency_overrides[get_db]()
    session = next(session_generator)
    session.add(
        OAuthConnection(
            platform="linkedin",
            account_name="example",
            encrypted_tokens="token",
            expires_at=datetime.now() - timedelta(hours=1),
        )
    )
    session.commit()
    session_generator.close()

    response = client.get("/api/oauth/linkedin/status")
    assert response.status_code == 200
    assert response.json()["connected"] is True
    assert response.json()["token_expired"] is True
