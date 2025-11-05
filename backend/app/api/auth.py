"""Authentication API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.core.database import get_db
from app.core.redis import RedisManager, get_redis
from app.utils.auth import (
    create_anonymous_user,
    register_user,
    login_user,
    refresh_access_token,
    revoke_token,
    revoke_all_user_tokens,
    get_current_user_from_token,
)
from app.schemas.user import UserResponse


router = APIRouter(prefix="/auth", tags=["authentication"])


# Request/Response Models
class AnonymousSessionResponse(BaseModel):
    """Response for anonymous session creation"""

    user: UserResponse
    session_token: str


class RegisterRequest(BaseModel):
    """Registration request"""

    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    """Login request"""

    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Authentication response with tokens"""

    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str


class RefreshResponse(BaseModel):
    """Refresh token response"""

    access_token: str
    token_type: str = "bearer"


# Endpoints
@router.post("/anonymous", response_model=AnonymousSessionResponse)
async def create_anonymous_session(db: AsyncSession = Depends(get_db)):
    """
    Create anonymous user session.

    This allows users to start chatting without registration.
    """
    user, session_token = await create_anonymous_user(db)

    return AnonymousSessionResponse(
        user=UserResponse.model_validate(user), session_token=session_token
    )


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register new user with email and password.

    Returns JWT tokens for authentication.
    """
    user, access_token, refresh_token = await register_user(
        request.email, request.password, db
    )

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Login user with email and password.

    Returns JWT tokens for authentication.
    """
    user, access_token, refresh_token = await login_user(
        request.email, request.password, db
    )

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis: RedisManager = Depends(get_redis),
):
    """
    Refresh access token using refresh token.

    This allows extending user session without re-login.
    """
    access_token = await refresh_access_token(request.refresh_token, db, redis)

    return RefreshResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    authorization: Optional[str] = Header(None),
    redis: RedisManager = Depends(get_redis),
):
    """
    Logout user by revoking current access token.

    Args:
        authorization: Authorization header with Bearer token
        redis: Redis manager for token blacklisting

    Returns:
        Success message
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = authorization.replace("Bearer ", "")

    # Revoke the token
    success = await revoke_token(token, redis)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to revoke token",
        )

    return {"message": "Successfully logged out"}


@router.post("/logout-all")
async def logout_all(
    db: AsyncSession = Depends(get_db),
    redis: RedisManager = Depends(get_redis),
    current_user = Depends(get_current_user_from_token),
):
    """
    Logout user from all devices by revoking all tokens.

    Args:
        db: Database session
        redis: Redis manager
        current_user: Current authenticated user

    Returns:
        Success message
    """
    user_id = str(current_user.user_id)

    # Revoke all tokens for this user
    success = await revoke_all_user_tokens(user_id, redis)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to revoke tokens",
        )

    return {"message": "Successfully logged out from all devices"}
