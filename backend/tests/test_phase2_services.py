import asyncio
import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.auth import verify_jwt
from app.config import Settings
from app.db import get_db
from app.models import ContentIdea, OAuthConnection, Source, SourceItem
from app.services import source_sync
from app.services.ingestion import compute_content_hash
from app.services.llm import IdeaGenerationError, LLMService
from app.services.quality import evaluate_draft_quality


def test_content_hash_deduplication():
    hash1 = compute_content_hash("  Sample Text Content  ")
    hash2 = compute_content_hash("sample text content")
    assert hash1 == hash2


def test_idea_generation_requires_ai_and_requests_five_ideas(monkeypatch):
    async def _test():
        llm = LLMService(Settings(inference_provider="template"))
        with pytest.raises(IdeaGenerationError) as error:
            await llm.generate_ideas("AI Trends 2026", "Content about recent advances in AI.")
        assert error.value.status_code == 503

        ai_llm = LLMService(Settings(inference_provider="openai"))
        response_ideas = [
            {
                "title": f"Idea {index}",
                "summary": "A source-grounded idea summary.",
                "proposed_angle": "A distinct angle.",
                "relevance_score": 85,
            }
            for index in range(5)
        ]

        async def fake_call(prompt):
            assert "exactly 5 distinct" in prompt
            return json.dumps(response_ideas)

        monkeypatch.setattr(ai_llm, "_call_openai_compatible", fake_call)
        ideas = await ai_llm.generate_ideas(
            "AI Trends 2026", "Content about recent advances in AI."
        )
        assert len(ideas) == 5

        async def invalid_call(_prompt):
            return "[]"

        monkeypatch.setattr(ai_llm, "_call_openai_compatible", invalid_call)
        with pytest.raises(IdeaGenerationError) as error:
            await ai_llm.generate_ideas(
                "AI Trends 2026", "Content about recent advances in AI."
            )
        assert error.value.status_code == 502

        async def failing_call(_prompt):
            raise RuntimeError("provider unavailable")

        monkeypatch.setattr(ai_llm, "_call_openai_compatible", failing_call)
        with pytest.raises(IdeaGenerationError) as error:
            await ai_llm.generate_ideas("AI Trends 2026", "Content about recent advances in AI.")
        assert error.value.status_code == 502

        # Draft generation retains its existing template fallback.
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


def test_delete_source_removes_its_ingested_items_but_preserves_ideas(client: TestClient):
    source_response = client.post(
        "/api/sources",
        json={
            "name": "Delete me",
            "source_type": "note",
            "uri_or_content": "This source will be deleted.",
        },
    )
    assert source_response.status_code == 200
    source_id = source_response.json()["id"]

    generator = client.app.dependency_overrides[get_db]()
    session = next(generator)
    session.add(
        ContentIdea(
            title="Idea retained",
            summary="Created from the source before deletion",
            source_type="generated",
            source_ref="Delete me",
        )
    )
    session.commit()
    generator.close()

    response = client.delete(f"/api/sources/{source_id}")

    assert response.status_code == 200
    assert response.json()["deleted_items"] == 1
    assert client.get("/api/sources").json() == []
    assert client.get("/api/sources/items").json() == []
    assert client.get("/api/content/ideas").json()[0]["title"] == "Idea retained"
    assert client.delete(f"/api/sources/{source_id}").status_code == 404


def test_scheduled_source_sync_continues_after_a_source_failure(client: TestClient, monkeypatch):
    generator = client.app.dependency_overrides[get_db]()
    session = next(generator)
    working_source = Source(
        name="Working note",
        source_type="note",
        uri_or_content="Fresh material",
        status="active",
    )
    failing_source = Source(
        name="Retry me",
        source_type="url",
        uri_or_content="https://example.invalid",
        status="active",
    )
    session.add_all([working_source, failing_source])
    session.commit()
    test_session_factory = sessionmaker(
        bind=session.get_bind(),
        autoflush=False,
        expire_on_commit=False,
    )
    working_id = working_source.id
    failing_id = failing_source.id
    generator.close()
    monkeypatch.setattr(source_sync, "SessionLocal", test_session_factory)

    class FakeIngestion:
        async def process_source(self, source):
            if source.id == failing_id:
                raise RuntimeError("Temporary fetch failure")
            return [
                {
                    "title": "Fresh material",
                    "author": "User Note",
                    "url": "",
                    "canonical_url": "",
                    "content": "Fresh material",
                    "content_hash": compute_content_hash("Fresh material"),
                    "published_at": datetime.now(),
                }
            ]

    monkeypatch.setattr(source_sync, "ingestion_service", FakeIngestion())

    asyncio.run(source_sync.sync_all_active_sources())

    generator = client.app.dependency_overrides[get_db]()
    session = next(generator)
    assert session.get(Source, working_id).last_fetched_at is not None
    assert session.query(SourceItem).filter_by(source_id=working_id).count() == 1
    assert session.get(Source, failing_id).status == "error"
    generator.close()


def test_idea_and_draft_generation_api(client: TestClient, monkeypatch):
    from app.routers import content as content_router

    async def fake_generate_ideas(*_args):
        return [
            {
                "title": f"Idea {index}",
                "summary": "A generated summary.",
                "proposed_angle": "A distinct perspective.",
                "relevance_score": 85,
            }
            for index in range(5)
        ]

    monkeypatch.setattr(content_router.llm_service, "generate_ideas", fake_generate_ideas)

    # Generate ideas from topic
    gen_ideas_resp = client.post(
        "/api/content/ideas/generate",
        json={
            "topic_title": "Local LLMs in 2026",
            "topic_content": "Running LLMs on consumer hardware.",
        },
    )
    assert gen_ideas_resp.status_code == 200
    ideas = gen_ideas_resp.json()
    assert len(ideas) == 5
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

    # Removing an idea hides it from the inbox while retaining associated drafts.
    remove_resp = client.delete(f"/api/content/ideas/{idea_id}")
    assert remove_resp.status_code == 200
    assert remove_resp.json() == {"archived": True}
    assert all(item["id"] != idea_id for item in client.get("/api/content/ideas").json())
    assert client.post(f"/api/content/ideas/{idea_id}/generate-drafts").status_code == 409
    drafts_after_removal = client.get("/api/content/drafts")
    assert drafts_after_removal.status_code == 200
    assert len(drafts_after_removal.json()) == 3
    assert all(draft["idea_id"] == idea_id for draft in drafts_after_removal.json())


def test_idea_generation_returns_clear_error_without_ai(client: TestClient, monkeypatch):
    from app.routers import content as content_router

    async def no_ai_configured(*_args):
        raise IdeaGenerationError(
            "AI-only idea generation is enabled, but no supported AI provider is configured.",
            status_code=503,
        )

    monkeypatch.setattr(content_router.llm_service, "generate_ideas", no_ai_configured)
    response = client.post(
        "/api/content/ideas/generate",
        json={"topic_title": "AI Trends", "topic_content": "Source content."},
    )
    assert response.status_code == 503
    assert "no supported AI provider is configured" in response.json()["detail"]


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
