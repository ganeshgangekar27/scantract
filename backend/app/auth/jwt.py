"""
JWT token encoding and decoding.

Uses PyJWT with HS256 algorithm.
"""
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

import jwt


# Get JWT secret from environment
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


def validate_jwt_secret():
    """
    Validate JWT_SECRET is set and secure.
    
    Raises:
        ValueError: If JWT_SECRET is missing or too short (except in test env)
    """
    env = os.getenv("ENV", "production")
    
    if env != "test":
        if not JWT_SECRET:
            raise ValueError(
                "JWT_SECRET environment variable is required for authentication. "
                "Generate a secure secret with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        
        if len(JWT_SECRET) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 characters long for security. "
                "Current length: {len(JWT_SECRET)}"
            )


def create_access_token(user_id: int, email: str) -> str:
    """
    Create a JWT access token for a user.
    
    Args:
        user_id: User ID
        email: User email
    
    Returns:
        JWT token string
    """
    expiry = datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expiry,
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload dict if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.InvalidTokenError:
        return None
