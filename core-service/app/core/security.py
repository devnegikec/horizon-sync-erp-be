"""Security utilities for JWT token validation"""

from jose import JWTError, jwt

from app.config import settings


def decode_token(token: str) -> dict | None:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None
