from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class TokenEncryptionError(Exception):
    pass


def _fernet() -> Fernet:
    key = get_settings().x_refresh_token_encryption_key
    if not key:
        raise TokenEncryptionError(
            "X refresh-token encryption is not configured. Set X_REFRESH_TOKEN_ENCRYPTION_KEY."
        )
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise TokenEncryptionError(
            "X_REFRESH_TOKEN_ENCRYPTION_KEY must be a valid Fernet key."
        ) from exc


def encrypt_refresh_token(token: str) -> str:
    return _fernet().encrypt(token.encode("utf-8")).decode("ascii")


def decrypt_refresh_token(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeEncodeError, UnicodeDecodeError) as exc:
        raise TokenEncryptionError(
            "Unable to decrypt the saved X refresh token. Check the configured encryption key."
        ) from exc
