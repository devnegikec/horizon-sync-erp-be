"""Security utilities for JWT token handling"""

from datetime import datetime, timedelta
from typing import Any, Optional

from jose import JWTError, jwt

from app.config import settings


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate JWT token.

    Args:
        token: JWT token string

    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None


def create_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT token.

    Args:
        data: Data to encode in token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_access_token(data: dict[str, Any]) -> str:
    """
    Create access token with default expiration.

    Args:
        data: Data to encode in token

    Returns:
        Encoded JWT access token
    """
    return create_token(data, expires_delta=timedelta(hours=1))
