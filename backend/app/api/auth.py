"""Authentication API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.utils.auth import (
    create_anonymous_user,
    register_user,
    login_user,
    refresh_access_token,
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
async def refresh(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    Refresh access token using refresh token.

    This allows extending user session without re-login.
    """
    access_token = await refresh_access_token(request.refresh_token, db)

    return RefreshResponse(access_token=access_token)
