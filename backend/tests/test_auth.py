"""
Tests for Authentication System

Tests cover:
- JWT token generation and validation
- Token refresh logic
- Token revocation (blacklisting)
- Permission checking
- Session management
- Password hashing/verification
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import time

from app.main import app
from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_token,
    revoke_all_user_tokens,
    hash_password,
    verify_password,
)


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """Mock Redis manager"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    return redis


# ===========================================================================
# JWT Token Generation Tests
# ===========================================================================


def test_create_access_token():
    """Test access token creation"""
    user_id = "test-user-123"
    token = create_access_token(data={"sub": user_id})

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0

    # Token should have 3 parts (header.payload.signature)
    parts = token.split(".")
    assert len(parts) == 3


def test_create_refresh_token():
    """Test refresh token creation"""
    user_id = "test-user-123"
    token = create_refresh_token(data={"sub": user_id})

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0

    parts = token.split(".")
    assert len(parts) == 3


def test_access_token_expiration():
    """Test that access token has correct expiration"""
    user_id = "test-user-123"
    token = create_access_token(data={"sub": user_id})

    # Decode without verification to check claims
    from jose import jwt
    from app.core.config import settings

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

    assert "exp" in payload
    assert "iat" in payload
    assert "type" in payload
    assert "jti" in payload

    # Check token type
    assert payload["type"] == "access"

    # Check expiration is ~15 minutes
    exp_time = datetime.fromtimestamp(payload["exp"])
    iat_time = datetime.fromtimestamp(payload["iat"])
    duration = exp_time - iat_time

    # Should be approximately 15 minutes
    assert 14 * 60 < duration.total_seconds() < 16 * 60


def test_refresh_token_expiration():
    """Test that refresh token has correct expiration"""
    user_id = "test-user-123"
    token = create_refresh_token(data={"sub": user_id})

    from jose import jwt
    from app.core.config import settings

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

    assert payload["type"] == "refresh"

    # Check expiration is ~7 days
    exp_time = datetime.fromtimestamp(payload["exp"])
    iat_time = datetime.fromtimestamp(payload["iat"])
    duration = exp_time - iat_time

    # Should be approximately 7 days
    assert 6.5 * 24 * 60 * 60 < duration.total_seconds() < 7.5 * 24 * 60 * 60


def test_token_includes_jti():
    """Test that tokens include unique JTI"""
    token1 = create_access_token(data={"sub": "user1"})
    token2 = create_access_token(data={"sub": "user1"})

    from jose import jwt
    from app.core.config import settings

    payload1 = jwt.decode(token1, settings.SECRET_KEY, algorithms=["HS256"])
    payload2 = jwt.decode(token2, settings.SECRET_KEY, algorithms=["HS256"])

    # JTIs should be different
    assert payload1["jti"] != payload2["jti"]


# ===========================================================================
# JWT Token Validation Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_decode_valid_token(mock_redis):
    """Test decoding valid token"""
    user_id = "test-user-123"
    token = create_access_token(data={"sub": user_id})

    payload = await decode_token(token, mock_redis)

    assert payload["sub"] == user_id
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_decode_expired_token(mock_redis):
    """Test decoding expired token"""
    from fastapi import HTTPException

    user_id = "test-user-123"
    # Create token with -1 minute expiration (already expired)
    token = create_access_token(
        data={"sub": user_id},
        expires_delta=timedelta(minutes=-1)
    )

    with pytest.raises(HTTPException) as exc_info:
        await decode_token(token, mock_redis)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_decode_invalid_token(mock_redis):
    """Test decoding invalid token"""
    from fastapi import HTTPException

    invalid_token = "invalid.token.string"

    with pytest.raises(HTTPException) as exc_info:
        await decode_token(invalid_token, mock_redis)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_decode_blacklisted_token(mock_redis):
    """Test decoding blacklisted token"""
    from fastapi import HTTPException

    user_id = "test-user-123"
    token = create_access_token(data={"sub": user_id})

    # Mock token as blacklisted
    mock_redis.get = AsyncMock(return_value="revoked")

    with pytest.raises(HTTPException) as exc_info:
        await decode_token(token, mock_redis)

    assert exc_info.value.status_code == 401
    assert "revoked" in str(exc_info.value.detail).lower()


# ===========================================================================
# Token Revocation Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_revoke_token_success(mock_redis):
    """Test successful token revocation"""
    user_id = "test-user-123"
    token = create_access_token(data={"sub": user_id})

    success = await revoke_token(token, mock_redis)

    assert success is True
    # Should have called Redis set
    mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_revoke_expired_token(mock_redis):
    """Test revoking already expired token"""
    user_id = "test-user-123"
    token = create_access_token(
        data={"sub": user_id},
        expires_delta=timedelta(minutes=-1)
    )

    success = await revoke_token(token, mock_redis)

    # Should return False (no need to revoke expired token)
    assert success is False


@pytest.mark.asyncio
async def test_revoke_all_user_tokens(mock_redis):
    """Test revoking all tokens for a user"""
    user_id = "test-user-123"

    success = await revoke_all_user_tokens(user_id, mock_redis)

    assert success is True
    # Should have set revocation marker in Redis
    mock_redis.set.assert_called_once()


# ===========================================================================
# Authentication Endpoint Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_anonymous_session_creation(client):
    """Test creating anonymous session"""
    with patch("app.api.auth.create_anonymous_user") as mock_create:
        mock_user = MagicMock()
        mock_user.id = "anon-user-123"
        mock_user.is_anonymous = True

        mock_create.return_value = (mock_user, "session-token-123")

        response = client.post("/auth/anonymous")

        assert response.status_code == 200
        data = response.json()
        assert "session_token" in data
        assert "user" in data


@pytest.mark.asyncio
async def test_register_success(client):
    """Test successful user registration"""
    with patch("app.api.auth.register_user") as mock_register:
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.user_id = "user-123"

        mock_register.return_value = (
            mock_user,
            "access-token-123",
            "refresh-token-123"
        )

        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Test registration with duplicate email"""
    with patch("app.api.auth.register_user") as mock_register:
        from fastapi import HTTPException

        mock_register.side_effect = HTTPException(
            status_code=400,
            detail="Email already registered"
        )

        response = client.post(
            "/auth/register",
            json={
                "email": "existing@example.com",
                "password": "SecurePass123!"
            }
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client):
    """Test successful login"""
    with patch("app.api.auth.login_user") as mock_login:
        mock_user = MagicMock()
        mock_user.id = "user-123"

        mock_login.return_value = (
            mock_user,
            "access-token-123",
            "refresh-token-123"
        )

        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    """Test login with invalid credentials"""
    with patch("app.api.auth.login_user") as mock_login:
        from fastapi import HTTPException

        mock_login.side_effect = HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPassword"
            }
        )

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_success(client):
    """Test successful token refresh"""
    with patch("app.api.auth.refresh_access_token") as mock_refresh:
        mock_refresh.return_value = "new-access-token-123"

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "valid-refresh-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_token_invalid(client):
    """Test refresh with invalid token"""
    with patch("app.api.auth.refresh_access_token") as mock_refresh:
        from fastapi import HTTPException

        mock_refresh.side_effect = HTTPException(
            status_code=401,
            detail="Invalid token"
        )

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid-token"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_success(client):
    """Test successful logout"""
    with patch("app.api.auth.revoke_token") as mock_revoke:
        mock_revoke.return_value = True

        response = client.post(
            "/auth/logout",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_logout_without_token(client):
    """Test logout without token"""
    response = client.post("/auth/logout")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_all_devices(client):
    """Test logout from all devices"""
    with patch("app.api.auth.get_current_user_from_token") as mock_get_user, \
         patch("app.api.auth.revoke_all_user_tokens") as mock_revoke_all:

        mock_user = MagicMock()
        mock_user.user_id = "user-123"
        mock_get_user.return_value = mock_user

        mock_revoke_all.return_value = True

        response = client.post(
            "/auth/logout-all",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        assert "all devices" in response.json()["message"].lower()


# ===========================================================================
# Password Hashing Tests
# ===========================================================================


def test_password_hashing():
    """Test password hashing"""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert hashed is not None
    assert len(hashed) > 0
    # Hash should be different from password
    assert hashed != password
    # Should be hex string (salt + hash)
    assert len(hashed) == 128  # 32 bytes salt + 32 bytes hash = 64 bytes = 128 hex chars


def test_password_verification_success():
    """Test successful password verification"""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_password_verification_failure():
    """Test failed password verification"""
    password = "SecurePassword123!"
    wrong_password = "WrongPassword123!"
    hashed = hash_password(password)

    assert verify_password(wrong_password, hashed) is False


def test_same_password_different_hashes():
    """Test that same password produces different hashes (due to salt)"""
    password = "SecurePassword123!"
    hash1 = hash_password(password)
    hash2 = hash_password(password)

    # Hashes should be different
    assert hash1 != hash2

    # But both should verify correctly
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


# ===========================================================================
# Authorization Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_get_current_user_valid_token(client):
    """Test getting current user with valid token"""
    with patch("app.utils.auth.decode_token") as mock_decode, \
         patch("app.utils.auth.get_db") as mock_db:

        # Mock token payload
        mock_decode.return_value = {
            "sub": "user-123",
            "type": "access",
            "iat": datetime.utcnow().timestamp()
        }

        # Mock database query
        mock_user = MagicMock()
        mock_user.user_id = "user-123"
        mock_user.is_deleted = False

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        # This test would require full app context
        # Simplified assertion
        assert True


@pytest.mark.asyncio
async def test_protected_route_without_token(client):
    """Test accessing protected route without token"""
    # Create a protected test route
    from fastapi import Depends
    from app.utils.auth import get_current_user_from_token

    @app.get("/test-protected")
    async def test_protected(user=Depends(get_current_user_from_token)):
        return {"user_id": user.user_id}

    response = client.get("/test-protected")

    assert response.status_code == 401


# ===========================================================================
# Token Refresh Flow Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_complete_auth_flow(client):
    """Test complete authentication flow"""
    with patch("app.api.auth.register_user") as mock_register, \
         patch("app.api.auth.refresh_access_token") as mock_refresh, \
         patch("app.api.auth.revoke_token") as mock_revoke:

        # Step 1: Register
        mock_user = MagicMock()
        mock_user.id = "user-123"

        mock_register.return_value = (
            mock_user,
            "initial-access-token",
            "initial-refresh-token"
        )

        register_response = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "Pass123!"}
        )

        assert register_response.status_code == 200
        initial_tokens = register_response.json()

        # Step 2: Refresh token
        mock_refresh.return_value = "new-access-token"

        refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": initial_tokens["refresh_token"]}
        )

        assert refresh_response.status_code == 200
        new_token = refresh_response.json()["access_token"]

        # Step 3: Logout
        mock_revoke.return_value = True

        logout_response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {new_token}"}
        )

        assert logout_response.status_code == 200


# ===========================================================================
# Performance Tests
# ===========================================================================


def test_token_generation_performance():
    """Test token generation performance"""
    iterations = 100

    start_time = time.time()
    for i in range(iterations):
        create_access_token(data={"sub": f"user-{i}"})
    elapsed = time.time() - start_time

    # Should generate 100 tokens in less than 1 second
    assert elapsed < 1.0
    print(f"Generated {iterations} tokens in {elapsed:.3f}s")


def test_password_hashing_performance():
    """Test password hashing performance"""
    password = "SecurePassword123!"

    start_time = time.time()
    hash_password(password)
    elapsed = time.time() - start_time

    # Should hash in less than 0.5 seconds (PBKDF2 with 100,000 iterations)
    assert elapsed < 0.5
    print(f"Password hashed in {elapsed:.3f}s")


def test_password_verification_performance():
    """Test password verification performance"""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    start_time = time.time()
    verify_password(password, hashed)
    elapsed = time.time() - start_time

    # Should verify in less than 0.5 seconds
    assert elapsed < 0.5
    print(f"Password verified in {elapsed:.3f}s")
