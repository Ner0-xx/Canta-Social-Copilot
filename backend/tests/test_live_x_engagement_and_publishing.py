import asyncio
from urllib.parse import parse_qs, urlparse

import pytest

from app.db import get_db
from app.models import (
    AppSettings,
    ContentDraft,
    ContentIdea,
    OAuthConnection,
    PlatformPublication,
)
from app.routers import content as content_router
from app.routers import engagement_api
from app.services.linkedin import LINKEDIN_API_VERSION, LinkedInService
from app.services.x_service import XAPIError, XService


def _connection(client, platform: str) -> None:
    generator = client.app.dependency_overrides[get_db]()
    session = next(generator)
    session.add(
        OAuthConnection(
            platform=platform,
            account_name="connected-account",
            encrypted_tokens="access-token",
        )
    )
    session.commit()
    generator.close()


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.is_error = status_code >= 400

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.is_error:
            raise AssertionError(f"Unexpected HTTP error {self.status_code}")


def test_x_authorization_requests_read_write_and_dm_read_scopes():
    service = XService()

    query = parse_qs(
        urlparse(service.get_authorization_url("https://app/callback", "state", "challenge")).query
    )

    assert set(query["scope"][0].split()) == set(service.AUTHORIZATION_SCOPES)
    assert "dm.read" in service.AUTHORIZATION_SCOPES


def test_x_service_maps_recent_posts_and_mentions(monkeypatch):
    requests = []

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, **kwargs):
            requests.append((url, kwargs))
            if url.endswith("/tweets"):
                return FakeResponse({"data": [{"id": "post-1", "text": "My post"}]})
            return FakeResponse(
                {
                    "data": [{"id": "mention-1", "text": "@me hello", "author_id": "user-2"}],
                    "includes": {
                        "users": [
                            {"id": "user-2", "name": "A Reader", "username": "reader"}
                        ]
                    },
                }
            )

    monkeypatch.setattr("app.services.x_service.httpx.AsyncClient", FakeClient)

    posts, mentions = asyncio.run(XService().get_recent_posts_and_mentions("token", "user-1", 15))

    assert posts[0]["text"] == "My post"
    assert mentions[0]["author"]["username"] == "reader"
    assert len(requests) == 2
    assert all(item[1]["params"]["max_results"] == 15 for item in requests)


def test_x_service_maps_dm_events_and_provider_errors(monkeypatch):
    captured = {}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, **kwargs):
            captured.update(kwargs)
            return FakeResponse({"data": [{"id": "dm-1"}]})

    monkeypatch.setattr("app.services.x_service.httpx.AsyncClient", FakeClient)

    result = asyncio.run(XService().get_dm_events("token"))

    assert result["data"][0]["id"] == "dm-1"
    assert captured["params"]["max_results"] == 100
    assert captured["params"]["event_types"] == "MessageCreate"
    assert "dm_event.fields" in captured["params"]

    class ForbiddenClient(FakeClient):
        async def get(self, url, **kwargs):
            return FakeResponse({}, status_code=403)

    monkeypatch.setattr("app.services.x_service.httpx.AsyncClient", ForbiddenClient)
    with pytest.raises(XAPIError) as error:
        asyncio.run(XService().get_dm_events("token"))
    assert error.value.status_code == 403


def test_x_engagement_endpoint_returns_live_provider_data(client, monkeypatch):
    _connection(client, "x")

    async def current_user(self, _token):
        return {"id": "user-1", "name": "Account", "username": "myaccount"}

    async def recent_data(self, _token, _user_id, _limit):
        return (
            [{"id": "post-1", "text": "My post"}],
            [
                {
                    "id": "mention-1",
                    "text": "@myaccount hello",
                    "author": {"name": "Reader", "username": "reader"},
                }
            ],
        )

    monkeypatch.setattr(engagement_api.XService, "get_current_user", current_user)
    monkeypatch.setattr(
        engagement_api.XService, "get_recent_posts_and_mentions", recent_data
    )

    response = client.get("/api/engagement/x")

    assert response.status_code == 200
    assert response.json()["account"]["username"] == "myaccount"
    assert response.json()["posts"][0]["url"] == "https://x.com/myaccount/status/post-1"
    assert response.json()["mentions"][0]["author"]["username"] == "reader"


def test_x_engagement_does_not_hide_provider_permission_errors(client, monkeypatch):
    _connection(client, "x")

    async def current_user(self, _token):
        raise XAPIError(403)

    monkeypatch.setattr(engagement_api.XService, "get_current_user", current_user)

    response = client.get("/api/engagement/x")

    assert response.status_code == 403
    assert "API access tier" in response.json()["detail"]


def test_x_dm_endpoint_groups_messages_by_conversation(client, monkeypatch):
    _connection(client, "x")

    async def current_user(self, _token):
        return {"id": "self", "name": "My Account", "username": "myaccount"}

    async def dm_events(self, _token):
        return {
            "data": [
                {
                    "id": "dm-2",
                    "dm_conversation_id": "conversation-1",
                    "sender_id": "self",
                    "text": "Thanks!",
                    "created_at": "2026-08-10T12:02:00Z",
                },
                {
                    "id": "dm-1",
                    "dm_conversation_id": "conversation-1",
                    "sender_id": "reader",
                    "text": "Hello",
                    "created_at": "2026-08-10T12:01:00Z",
                },
            ],
            "includes": {
                "users": [{"id": "reader", "name": "A Reader", "username": "reader"}]
            },
        }

    monkeypatch.setattr(engagement_api.XService, "get_current_user", current_user)
    monkeypatch.setattr(engagement_api.XService, "get_dm_events", dm_events)

    response = client.get("/api/engagement/x/direct-messages")

    assert response.status_code == 200
    conversation = response.json()["conversations"][0]
    assert conversation["participant"] == "A Reader"
    assert [message["text"] for message in conversation["messages"]] == ["Hello", "Thanks!"]
    assert conversation["messages"][1]["is_me"] is True


@pytest.mark.parametrize("platform", ["x", "linkedin"])
def test_manual_publish_calls_the_selected_provider(client, monkeypatch, platform):
    generator = client.app.dependency_overrides[get_db]()
    session = next(generator)
    session.add(AppSettings(id=1, release_level="integrate", publishing_enabled=True))
    session.add(
        OAuthConnection(
            platform=platform,
            account_name="connected-account",
            encrypted_tokens="access-token",
        )
    )
    idea = ContentIdea(title="Publish test", summary="Test post", source_type="note")
    session.add(idea)
    session.flush()
    draft = ContentDraft(
        idea_id=idea.id,
        platform=platform,
        title="Publish test",
        body="A real provider publish call is required.",
        status="approved",
    )
    session.add(draft)
    session.commit()
    draft_id = draft.id
    generator.close()
    calls = []

    async def fake_publish(self, access_token, text, image_path=None):
        calls.append((access_token, text, image_path))
        return f"{platform}-post-123"

    service = content_router.XService if platform == "x" else content_router.LinkedInService
    monkeypatch.setattr(service, "publish_post", fake_publish)

    response = client.post(f"/api/content/drafts/{draft_id}/publish-manual")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "published"
    assert calls == [("access-token", "A real provider publish call is required.", None)]

    generator = client.app.dependency_overrides[get_db]()
    session = next(generator)
    publication = (
        session.query(PlatformPublication)
        .filter_by(draft_id=draft_id, platform=platform)
        .one()
    )
    assert publication.platform_post_id == f"{platform}-post-123"
    generator.close()


def test_linkedin_service_uses_posts_api(monkeypatch):
    service = LinkedInService()

    async def user_profile(_token):
        return {"sub": "member-1"}

    monkeypatch.setattr(service, "get_user_profile", user_profile)
    captured = {}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured.update(kwargs)
            return FakeResponse({}, status_code=201, headers={"X-RestLi-Id": "post-123"})

    monkeypatch.setattr("app.services.linkedin.httpx.AsyncClient", FakeClient)

    post_id = asyncio.run(service.publish_post("token", "Hello LinkedIn"))

    assert post_id == "post-123"
    assert captured["url"] == "https://api.linkedin.com/rest/posts"
    assert captured["headers"]["Linkedin-Version"] == LINKEDIN_API_VERSION
    assert captured["json"]["author"] == "urn:li:person:member-1"
    assert captured["json"]["commentary"] == "Hello LinkedIn"


def test_x_service_publishes_through_posts_api(monkeypatch):
    captured = {}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured.update(kwargs)
            return FakeResponse({"data": {"id": "post-456"}}, status_code=201)

    monkeypatch.setattr("app.services.x_service.httpx.AsyncClient", FakeClient)

    post_id = asyncio.run(XService().publish_post("token", "Hello X"))

    assert post_id == "post-456"
    assert captured["url"] == "https://api.x.com/2/tweets"
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert captured["json"] == {"text": "Hello X"}
