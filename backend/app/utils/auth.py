"""Authentication and authorization utilities"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.utils.encryption import encryption_service


# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Data to encode in token
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token (longer expiration)"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and verify JWT token.

    Args:
        token: JWT token to decode

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_from_token(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current user from JWT token.

    Args:
        authorization: Authorization header (Bearer token)
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)

    # Verify token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # Get user ID from token
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Get user from database
    result = await db.execute(
        select(User).where(User.user_id == user_id, User.is_deleted == False)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update last active
    user.last_active = datetime.utcnow()
    await db.commit()

    return user


async def get_current_user_from_session(
    session_token: str, db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current user from session token (simpler auth for chat).

    Args:
        session_token: Session token
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If session is invalid or user not found
    """
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session token",
        )

    # Get user from database
    result = await db.execute(
        select(User).where(
            User.session_token == session_token, User.is_deleted == False
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
        )

    # Update last active
    user.last_active = datetime.utcnow()
    await db.commit()

    return user


async def create_anonymous_user(db: AsyncSession) -> tuple[User, str]:
    """
    Create anonymous user with session token.

    Args:
        db: Database session

    Returns:
        Tuple of (User, session_token)
    """
    session_token = encryption_service.generate_session_token()

    user = User(
        is_anonymous=True,
        session_token=session_token,
        consent_given=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user, session_token


async def register_user(
    email: str, password: str, db: AsyncSession
) -> tuple[User, str, str]:
    """
    Register new user with email and password.

    Args:
        email: User email
        password: User password
        db: Database session

    Returns:
        Tuple of (User, access_token, refresh_token)

    Raises:
        HTTPException: If email already exists
    """
    # Check if email already exists
    email_hash = encryption_service.hash_email(email)

    result = await db.execute(
        select(User).where(User.email_hash == email_hash, User.is_deleted == False)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Encrypt email
    email_encrypted, email_hash = encryption_service.encrypt_email(email)

    # Hash password
    password_hash = encryption_service.hash_password(password)

    # Create session token
    session_token = encryption_service.generate_session_token()

    # Create user
    user = User(
        email_encrypted=email_encrypted,
        email_hash=email_hash,
        is_anonymous=False,
        session_token=session_token,
        consent_given=True,
        consent_timestamp=datetime.utcnow(),
        metadata={"password_hash": password_hash},
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.user_id)})
    refresh_token = create_refresh_token(data={"sub": str(user.user_id)})

    return user, access_token, refresh_token


async def login_user(
    email: str, password: str, db: AsyncSession
) -> tuple[User, str, str]:
    """
    Login user with email and password.

    Args:
        email: User email
        password: User password
        db: Database session

    Returns:
        Tuple of (User, access_token, refresh_token)

    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by email hash
    email_hash = encryption_service.hash_email(email)

    result = await db.execute(
        select(User).where(User.email_hash == email_hash, User.is_deleted == False)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Verify password
    password_hash = user.metadata.get("password_hash")
    if not password_hash or not encryption_service.verify_password(
        password, password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.user_id)})
    refresh_token = create_refresh_token(data={"sub": str(user.user_id)})

    return user, access_token, refresh_token


async def refresh_access_token(refresh_token: str, db: AsyncSession) -> str:
    """
    Refresh access token using refresh token.

    Args:
        refresh_token: Refresh token
        db: Database session

    Returns:
        New access token

    Raises:
        HTTPException: If refresh token is invalid
    """
    payload = decode_token(refresh_token)

    # Verify token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Verify user exists
    result = await db.execute(
        select(User).where(User.user_id == user_id, User.is_deleted == False)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Create new access token
    access_token = create_access_token(data={"sub": str(user.user_id)})

    return access_token


def require_consent(user: User = Depends(get_current_user_from_token)) -> User:
    """
    Dependency to require user consent.

    Raises:
        HTTPException: If user hasn't given consent
    """
    if not user.consent_given:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User consent required",
        )
    return user
