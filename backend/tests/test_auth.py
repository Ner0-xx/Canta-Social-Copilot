from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app import auth


class FakeJwksClient:
    def __init__(self, public_key):
        self.public_key = public_key

    def get_signing_key_from_jwt(self, _token):
        return SimpleNamespace(key=self.public_key)


@pytest.fixture
def signing_keys():
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()


@pytest.fixture
def auth_settings(monkeypatch, signing_keys):
    private_key, public_key = signing_keys
    settings = SimpleNamespace(
        app_env="production",
        supabase_url="https://project.supabase.co",
        supabase_jwks_url="",
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(
        auth,
        "_get_jwks_client",
        lambda _url: FakeJwksClient(public_key),
    )
    return private_key


def issue_token(
    private_key,
    *,
    issuer="https://project.supabase.co/auth/v1",
    audience="authenticated",
):
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": "user-123",
            "iss": issuer,
            "aud": audience,
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        private_key,
        algorithm="ES256",
        headers={"kid": "test-key"},
    )


def bearer(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_verify_jwt_accepts_supabase_es256_token(auth_settings):
    token = issue_token(auth_settings)

    payload = auth.verify_jwt(bearer(token))

    assert payload["sub"] == "user-123"


@pytest.mark.parametrize(
    ("issuer", "audience"),
    [
        ("https://another-project.supabase.co/auth/v1", "authenticated"),
        ("https://project.supabase.co/auth/v1", "anon"),
    ],
)
def test_verify_jwt_rejects_wrong_issuer_or_audience(auth_settings, issuer, audience):
    token = issue_token(auth_settings, issuer=issuer, audience=audience)

    with pytest.raises(HTTPException) as exc_info:
        auth.verify_jwt(bearer(token))

    assert exc_info.value.status_code == 401


def test_verify_jwt_rejects_non_es256_token(auth_settings):
    token = jwt.encode(
        {
            "sub": "user-123",
            "iss": "https://project.supabase.co/auth/v1",
            "aud": "authenticated",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "not-an-es256-key-with-at-least-32-bytes",
        algorithm="HS256",
        headers={"kid": "test-key"},
    )

    with pytest.raises(HTTPException) as exc_info:
        auth.verify_jwt(bearer(token))

    assert exc_info.value.status_code == 401
