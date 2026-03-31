# auth.py
from datetime import UTC, datetime, timedelta

import jwt
from fastapi.security import OAuth2PasswordBearer # OAuth2 
from pwdlib import PasswordHash
from config import settings

from fastapi import Depends, HTTPException, status
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import models
from database import get_db

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/token")

def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes,
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )
    return encoded_jwt


def verify_access_token(token: str) -> str | None:
    """Verify a JWT access token and return the subject (user id) if valid."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError:
        return None
    else:  # try / except / else
        return payload.get("sub")
    


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],  # token: str = Depends(oauth2_scheme),
    db: Annotated[AsyncSession, Depends(get_db)],  # db: AsyncSession = Depends(get_db),
) -> models.User:
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(
        select(models.User).where(models.User.id == user_id_int),
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[models.User, Depends(get_current_user)] # convenience type alias that makes code cleaner and more readable

"""
OAuth2:
OAuth 2.0 is an authorization framework,  It allows applications to obtain limited access to user accounts on an HTTP service.
(for 3rd-party clients, Social login, Public API)
In FastAPI, OAuth2 is a standard way to handle authentication and authorization using access tokens—usually Bearer tokens sent in the Authorization header.
rules for how a user proves who they are and what they're allowed to do, without sharing passwords with every app.

flow -> 
User logs in with username/password, 
Server verifies credentials, 
Server issues an access token (usually a JWT), 
Client sends this token with every request: Authorization: Bearer <token>

for user authorization, although FastAPI 'recommend' OAuth2, using JWT alone is perfectly fine.
OAuth2 gives: Swagger UI login button 🔐, Standardized error handling, Cleaner dependency helpers, Easier future expansion.
Smart middle ground: JWT + OAuth2PasswordBearer. (not implementing full OAuth2, use OAuth2 as a wrapper for JWT)

OAuth2PasswordRequestForm  → login
OAuth2PasswordBearer      → protected routes
OAuth2PasswordBearer: 
A dependency that looks for a Bearer token in the Authorization header of incoming requests. Extracts the token, Raises 401 if missing
"""