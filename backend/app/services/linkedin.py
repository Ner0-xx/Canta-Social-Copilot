from urllib.parse import urlencode

import httpx

from app.config import get_settings
from app.services.draft_image import load_draft_image

LINKEDIN_API_VERSION = "202609"


class LinkedInService:
    def __init__(self):
        self.settings = get_settings()
        self.client_id = self.settings.linkedin_client_id
        self.client_secret = self.settings.linkedin_client_secret

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": "w_member_social openid profile email",
        }
        return f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_user_profile(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    def _api_headers(self, access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Linkedin-Version": LINKEDIN_API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def publish_post(self, access_token: str, text: str, image_path: str = None) -> str:
        profile = await self.get_user_profile(access_token)
        person_urn = f"urn:li:person:{profile.get('sub')}"
        headers = self._api_headers(access_token)
        image_urn = None

        if image_path:
            image_bytes, _, content_type = await load_draft_image(image_path)
            async with httpx.AsyncClient() as client:
                init_response = await client.post(
                    "https://api.linkedin.com/rest/images?action=initializeUpload",
                    headers=headers,
                    json={"initializeUploadRequest": {"owner": person_urn}},
                )
                init_response.raise_for_status()
                upload_data = init_response.json().get("value", {})
                upload_url = upload_data.get("uploadUrl")
                image_urn = upload_data.get("image")
                if not upload_url or not image_urn:
                    raise ValueError("LinkedIn did not return the image upload details.")

                upload_response = await client.put(
                    upload_url,
                    content=image_bytes,
                    headers={"Content-Type": content_type},
                )
                upload_response.raise_for_status()

        post_data = {
            "author": person_urn,
            "commentary": text,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        if image_urn:
            post_data["content"] = {
                "media": {
                    "title": "Image",
                    "id": image_urn,
                }
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linkedin.com/rest/posts",
                headers=headers,
                json=post_data,
            )
        response.raise_for_status()
        post_id = response.headers.get("X-RestLi-Id")
        if not post_id:
            raise ValueError("LinkedIn did not return a post ID after publishing.")
        return post_id
