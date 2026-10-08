from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import OAuthConnection
from app.services.token_crypto import decrypt_refresh_token, encrypt_refresh_token
from app.services.x_service import XService

REFRESH_EARLY_SECONDS = 300


def needs_x_token_refresh(connection: OAuthConnection, now: datetime | None = None) -> bool:
    if not connection.expires_at or not connection.encrypted_refresh_token:
        return False
    now = now or datetime.now(UTC).replace(tzinfo=None)
    return connection.expires_at <= now + timedelta(seconds=REFRESH_EARLY_SECONDS)


async def refresh_x_connection(
    connection: OAuthConnection,
    session: Session,
    service: XService | None = None,
) -> bool:
    if not needs_x_token_refresh(connection):
        return False
    if not connection.encrypted_refresh_token:
        raise ValueError(
            "No X refresh token is saved. Reconnect X and approve the offline.access permission."
        )

    refresh_token = decrypt_refresh_token(connection.encrypted_refresh_token)
    token_data = await (service or XService()).refresh_access_token(refresh_token)
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in")
    if not isinstance(access_token, str) or not access_token:
        raise ValueError("X did not return a new access token.")
    if not isinstance(expires_in, (int, float)) or expires_in <= 0:
        raise ValueError("X did not return a valid access-token lifetime.")

    rotated_refresh_token = token_data.get("refresh_token")
    connection.encrypted_tokens = access_token
    if rotated_refresh_token:
        connection.encrypted_refresh_token = encrypt_refresh_token(rotated_refresh_token)
    connection.expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
        seconds=expires_in
    )
    session.commit()
    return True
