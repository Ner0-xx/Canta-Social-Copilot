from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

security = HTTPBearer()


@lru_cache(maxsize=1)
def _get_jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url, cache_jwk_set=True, timeout=5)


def verify_jwt(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
):
    settings = get_settings()
    supabase_url = settings.supabase_url.rstrip("/")
    if not supabase_url:
        if settings.app_env.lower() == "development":
            return "local_user"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase JWT verification is not configured",
        )

    jwks_url = settings.supabase_jwks_url or (
        f"{supabase_url}/auth/v1/.well-known/jwks.json"
    )
    issuer = f"{supabase_url}/auth/v1"
    token = credentials.credentials

    try:
        signing_key = _get_jwks_client(jwks_url).get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["ES256"],
            audience="authenticated",
            issuer=issuer,
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve Supabase signing keys",
        ) from exc
    except (jwt.InvalidTokenError, jwt.PyJWKClientError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
