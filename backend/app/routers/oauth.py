import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import OAuthConnection
from app.schemas import OAuthConnectionData
from app.services.linkedin import LinkedInService
from app.services.x_service import XService

logger = logging.getLogger(__name__)

# Simple in-memory store for PKCE state
pkce_store = {}

router = APIRouter(prefix="/oauth", tags=["oauth"])

class OAuthStatusResponse(BaseModel):
    connected: bool
    platform: str
    account_name: str | None = None
    expires_at: datetime | None = None

@router.get("/{platform}/status", response_model=OAuthStatusResponse)
def get_oauth_status(platform: str, session: Session = Depends(get_db)):
    conn = session.query(OAuthConnection).filter_by(platform=platform).first()
    if not conn:
        return OAuthStatusResponse(connected=False, platform=platform)
        
    is_expired = conn.expires_at and conn.expires_at < datetime.now(timezone.utc).replace(tzinfo=None)
    
    return OAuthStatusResponse(
        connected=not is_expired,
        platform=platform,
        account_name=conn.account_name,
        expires_at=conn.expires_at
    )

@router.get("/{platform}/login")
def oauth_login(platform: str, request: Request):
    if platform not in ["linkedin", "x"]:
        raise HTTPException(status_code=400, detail="Unsupported platform")
        
    redirect_uri = str(request.url_for("oauth_callback", platform=platform))
    state = "xyz123"
    
    if platform == "linkedin":
        linkedin = LinkedInService()
        url = linkedin.get_authorization_url(redirect_uri=redirect_uri, state=state)
    elif platform == "x":
        x_svc = XService()
        verifier = x_svc.generate_pkce_verifier()
        challenge = x_svc.generate_pkce_challenge(verifier)
        pkce_store[state] = verifier
        url = x_svc.get_authorization_url(redirect_uri=redirect_uri, state=state, code_challenge=challenge)
        
    return RedirectResponse(url)

@router.get("/{platform}/callback")
async def oauth_callback(
    platform: str, 
    request: Request,
    code: str = Query(None), 
    state: str = Query(None),
    error: str = Query(None),
    error_description: str = Query(None),
    session: Session = Depends(get_db)
):
    if error:
        logger.error(f"OAuth error: {error} - {error_description}")
        return RedirectResponse(f"http://127.0.0.1:5173/settings?error={error}")

    if not code:
        return RedirectResponse("http://127.0.0.1:5173/settings?error=no_code")

    if platform not in ["linkedin", "x"]:
        raise HTTPException(status_code=400, detail="Unsupported platform")

    redirect_uri = str(request.url_for("oauth_callback", platform=platform))
    
    try:
        if platform == "linkedin":
            linkedin = LinkedInService()
            token_data = await linkedin.exchange_code_for_token(code, redirect_uri)
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 5184000)
            
            profile = await linkedin.get_user_profile(access_token)
            account_name = profile.get("name", "LinkedIn User")
            scopes = ["w_member_social", "openid", "profile", "email"]
            
        elif platform == "x":
            x_svc = XService()
            verifier = pkce_store.pop(state, None)
            if not verifier:
                return RedirectResponse("http://127.0.0.1:5173/settings?error=pkce_missing")
                
            token_data = await x_svc.exchange_code_for_token(code, redirect_uri, verifier)
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 7200) # X tokens usually expire in 2 hours
            
            profile = await x_svc.get_user_profile(access_token)
            account_name = profile.get("username", "X User")
            scopes = ["tweet.read", "tweet.write", "users.read", "offline.access"]
            
        conn = session.query(OAuthConnection).filter_by(platform=platform).first()
        if not conn:
            conn = OAuthConnection(platform=platform)
            session.add(conn)
            
        conn.account_name = account_name
        conn.encrypted_tokens = access_token
        conn.scopes = scopes
        conn.expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        session.commit()
        
        return RedirectResponse("http://127.0.0.1:5173/settings?success=1")
    except Exception as e:
        logger.error(f"Failed to exchange token: {e}")
        return RedirectResponse("http://127.0.0.1:5173/settings?error=token_exchange_failed")
