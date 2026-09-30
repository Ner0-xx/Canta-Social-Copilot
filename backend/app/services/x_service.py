import base64
import hashlib
import os
import httpx
from urllib.parse import urlencode
from app.config import get_settings

class XService:
    def __init__(self):
        self.settings = get_settings()
        self.client_id = self.settings.x_client_id
        self.client_secret = self.settings.x_client_secret

    @staticmethod
    def generate_pkce_verifier() -> str:
        # Generate 32 bytes of randomness and base64 url-encode
        verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode('utf-8')
        return verifier

    @staticmethod
    def generate_pkce_challenge(verifier: str) -> str:
        # SHA256 hash the verifier, then base64 url-encode
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('utf-8')
        return challenge

    def get_authorization_url(self, redirect_uri: str, state: str, code_challenge: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "tweet.read tweet.write users.read offline.access",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"https://twitter.com/i/oauth2/authorize?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str, redirect_uri: str, code_verifier: str) -> dict:
        url = "https://api.twitter.com/2/oauth2/token"
        
        # X requires client credentials in Basic Auth header
        auth_string = f"{self.client_id}:{self.client_secret}"
        b64_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        
        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=data, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def get_user_profile(self, access_token: str) -> dict:
        url = "https://api.twitter.com/2/users/me"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json().get("data", {})

    async def publish_post(self, access_token: str, text: str, image_path: str = None) -> str:
        media_id = None
        
        if image_path:
            local_path = f"data{image_path}"
            media_url = "https://upload.twitter.com/1.1/media/upload.json"
            media_headers = {
                "Authorization": f"Bearer {access_token}"
            }
            with open(local_path, "rb") as f:
                files = {"media": f}
                async with httpx.AsyncClient() as client:
                    media_resp = await client.post(media_url, headers=media_headers, files=files)
                    media_resp.raise_for_status()
                    media_id = media_resp.json().get("media_id_string")

        url = "https://api.twitter.com/2/tweets"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "text": text
        }
        
        if media_id:
            data["media"] = {"media_ids": [media_id]}

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=data)
            resp.raise_for_status()
            return resp.json().get("data", {}).get("id", "x-post-id")
