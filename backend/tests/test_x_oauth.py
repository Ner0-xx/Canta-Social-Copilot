import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base, get_db
from app.models import OAuthConnection
from app.routers import oauth as oauth_router
from app.services import token_crypto
from app.services.token_crypto import decrypt_refresh_token, encrypt_refresh_token
from app.services.x_oauth import needs_x_token_refresh, refresh_x_connection
from app.services.x_service import XService


def configure_encryption(monkeypatch):
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(
        token_crypto,
        "get_settings",
        lambda: SimpleNamespace(x_refresh_token_encryption_key=key),
    )
    return key


def test_refresh_token_is_encrypted_at_rest(monkeypatch):
    configure_encryption(monkeypatch)

    encrypted = encrypt_refresh_token("refresh-secret")

    assert encrypted != "refresh-secret"
    assert decrypt_refresh_token(encrypted) == "refresh-secret"


def test_needs_refresh_before_expiry():
    connection = OAuthConnection(
        platform="x",
        encrypted_tokens="access",
        encrypted_refresh_token="encrypted-refresh",
        expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=4),
    )

    assert needs_x_token_refresh(connection)


def test_refresh_x_connection_saves_rotated_tokens_and_expiry(monkeypatch):
    configure_encryption(monkeypatch)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    class FakeXService:
        async def refresh_access_token(self, refresh_token):
            assert refresh_token == "current-refresh"
            return {
                "access_token": "new-access",
                "refresh_token": "rotated-refresh",
                "expires_in": 7200,
            }

    with Session(engine) as session:
        connection = OAuthConnection(
            platform="x",
            account_name="test-account",
            encrypted_tokens="old-access",
            encrypted_refresh_token=encrypt_refresh_token("current-refresh"),
            expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1),
        )
        session.add(connection)
        session.commit()

        refreshed = asyncio.run(
            refresh_x_connection(connection, session, service=FakeXService())
        )

        assert refreshed is True
        assert connection.encrypted_tokens == "new-access"
        assert decrypt_refresh_token(connection.encrypted_refresh_token) == "rotated-refresh"
        assert connection.expires_at > datetime.now(UTC).replace(tzinfo=None)


def test_refresh_x_connection_noops_when_token_is_not_near_expiry():
    connection = OAuthConnection(
        platform="x",
        encrypted_tokens="access",
        encrypted_refresh_token="encrypted-refresh",
        expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
    )

    assert not needs_x_token_refresh(connection)


def test_x_service_sends_refresh_grant(monkeypatch):
    service = XService()
    captured = {}

    async def capture_request(data):
        captured.update(data)
        return {"access_token": "new-access"}

    monkeypatch.setattr(service, "_request_token", capture_request)

    response = asyncio.run(service.refresh_access_token("refresh-secret"))

    assert captured == {
        "grant_type": "refresh_token",
        "refresh_token": "refresh-secret",
        "client_id": service.client_id,
    }
    assert response["access_token"] == "new-access"


def test_refresh_endpoint_returns_updated_connection_status(client, monkeypatch):
    session_generator = client.app.dependency_overrides[get_db]()
    session = next(session_generator)
    connection = OAuthConnection(
        platform="x",
        account_name="test-account",
        encrypted_tokens="old-access",
        encrypted_refresh_token="encrypted-refresh",
        expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1),
    )
    session.add(connection)
    session.commit()
    session_generator.close()

    async def fake_refresh(connection, session):
        connection.encrypted_tokens = "new-access"
        connection.expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=2)
        session.commit()

    monkeypatch.setattr(oauth_router, "refresh_x_connection", fake_refresh)

    response = client.post(
        "/api/oauth/x/refresh",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()["connected"] is True
    assert response.json()["token_expired"] is False
    assert response.json()["refresh_token_available"] is True
