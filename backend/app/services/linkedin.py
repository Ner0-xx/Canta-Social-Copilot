import httpx
import os
from urllib.parse import urlencode
from app.config import get_settings

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
        url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=data)
            resp.raise_for_status()
            return resp.json()

    async def get_user_profile(self, access_token: str) -> dict:
        url = "https://api.linkedin.com/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def publish_post(self, access_token: str, text: str, image_path: str = None) -> str:
        # First get the user's URN
        profile = await self.get_user_profile(access_token)
        person_urn = f"urn:li:person:{profile.get('sub')}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        asset_urn = None
        if image_path:
            # Step 1: Register upload
            register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
            register_data = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": person_urn,
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }
                    ]
                }
            }
            async with httpx.AsyncClient() as client:
                reg_resp = await client.post(register_url, headers=headers, json=register_data)
                reg_resp.raise_for_status()
                reg_json = reg_resp.json()
                upload_url = reg_json["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
                asset_urn = reg_json["value"]["asset"]
                
                # Step 2: Upload the binary image
                # Map logical image_path back to physical data/uploads
                # e.g. /uploads/123.jpg -> data/uploads/123.jpg
                local_path = f"data{image_path}"
                with open(local_path, "rb") as f:
                    upload_headers = {"Authorization": f"Bearer {access_token}"}
                    upload_resp = await client.post(upload_url, headers=upload_headers, content=f.read())
                    upload_resp.raise_for_status()

        # Step 3: Create Post
        url = "https://api.linkedin.com/v2/ugcPosts"
        data = {
            "author": person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "IMAGE" if asset_urn else "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        if asset_urn:
            data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                {
                    "status": "READY",
                    "media": asset_urn
                }
            ]

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=data)
            resp.raise_for_status()
            return resp.headers.get("X-RestLi-Id", resp.json().get("id", "linkedin-post-id"))
