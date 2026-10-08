import asyncio
import base64
import hashlib
import os
from urllib.parse import urlencode

import httpx

from app.config import get_settings
from app.services.draft_image import load_draft_image


class XAPIError(Exception):
    def __init__(self, status_code: int):
        self.status_code = status_code
        if status_code == 401:
            message = "X rejected the saved access token. Refresh or reconnect the X account."
        elif status_code == 403:
            message = "X denied this request. Check the account permissions and X API access tier."
        elif status_code == 429:
            message = "X API rate limit reached. Wait a while, then try again."
        else:
            message = f"X API request failed with status {status_code}."
        super().__init__(message)


class XService:
    AUTHORIZATION_SCOPES = (
        "tweet.read",
        "tweet.write",
        "users.read",
        "dm.read",
        "offline.access",
    )

    def __init__(self):
        self.settings = get_settings()
        self.client_id = self.settings.x_client_id
        self.client_secret = self.settings.x_client_secret

    @staticmethod
    def generate_pkce_verifier() -> str:
        return base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("utf-8")

    @staticmethod
    def generate_pkce_challenge(verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")

    def get_authorization_url(self, redirect_uri: str, state: str, code_challenge: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.AUTHORIZATION_SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"https://twitter.com/i/oauth2/authorize?{urlencode(params)}"

    def _token_headers(self) -> dict[str, str]:
        auth_string = f"{self.client_id}:{self.client_secret}"
        b64_auth = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
        return {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    async def _request_token(self, data: dict[str, str]) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.twitter.com/2/oauth2/token",
                data=data,
                headers=self._token_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def exchange_code_for_token(
        self, code: str, redirect_uri: str, code_verifier: str
    ) -> dict:
        return await self._request_token(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "code_verifier": code_verifier,
            }
        )

    async def refresh_access_token(self, refresh_token: str) -> dict:
        return await self._request_token(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
            }
        )

    async def get_user_profile(self, access_token: str) -> dict:
        return await self.get_current_user(access_token)

    async def get_current_user(self, access_token: str) -> dict:
        return (await self._api_get("users/me", access_token)).get("data", {})

    async def get_recent_posts_and_mentions(
        self, access_token: str, user_id: str, limit: int = 20
    ) -> tuple[list[dict], list[dict]]:
        fields = "created_at,conversation_id,public_metrics,reply_settings"
        posts, mentions = await asyncio.gather(
            self._api_get(
                f"users/{user_id}/tweets",
                access_token,
                {"max_results": limit, "tweet.fields": fields},
            ),
            self._api_get(
                f"users/{user_id}/mentions",
                access_token,
                {
                    "max_results": limit,
                    "tweet.fields": fields,
                    "expansions": "author_id",
                    "user.fields": "id,name,username,profile_image_url",
                },
            ),
        )
        users = {
            user["id"]: user
            for user in mentions.get("includes", {}).get("users", [])
            if isinstance(user, dict) and user.get("id")
        }
        normalized_mentions = [
            {
                **mention,
                "author": users.get(mention.get("author_id"), {}),
            }
            for mention in mentions.get("data", [])
            if isinstance(mention, dict)
        ]
        return posts.get("data", []), normalized_mentions

    async def get_dm_events(self, access_token: str, limit: int = 100) -> dict:
        return await self._api_get(
            "dm_events",
            access_token,
            {
                "max_results": limit,
                "event_types": "MessageCreate",
                "dm_event.fields": "created_at,dm_conversation_id,event_type,id,text",
                "expansions": "sender_id,participant_ids",
                "user.fields": "id,name,username,profile_image_url",
            },
        )

    async def _api_get(
        self, endpoint: str, access_token: str, params: dict | None = None
    ) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.x.com/2/{endpoint}",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
        if response.is_error:
            raise XAPIError(response.status_code)
        return response.json()

    async def publish_post(self, access_token: str, text: str, image_path: str = None) -> str:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        data: dict[str, object] = {"text": text}

        if image_path:
            image_bytes, filename, content_type = await load_draft_image(image_path)
            async with httpx.AsyncClient() as client:
                media_response = await client.post(
                    "https://upload.twitter.com/1.1/media/upload.json",
                    headers={"Authorization": f"Bearer {access_token}"},
                    files={"media": (filename, image_bytes, content_type)},
                )
                media_response.raise_for_status()
                media_id = media_response.json().get("media_id_string")
            if not media_id:
                raise ValueError("X did not return a media ID for the uploaded image.")
            data["media"] = {"media_ids": [media_id]}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.x.com/2/tweets",
                headers=headers,
                json=data,
            )
        if response.is_error:
            raise XAPIError(response.status_code)
        post_id = response.json().get("data", {}).get("id")
        if not post_id:
            raise ValueError("X did not return a post ID after publishing.")
        return post_id
