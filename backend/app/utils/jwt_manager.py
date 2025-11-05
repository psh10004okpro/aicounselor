"""
JWT Authentication and Authorization Utilities

Implements:
- JWT token generation and validation
- Access Token (15 minutes) + Refresh Token (7 days)
- Redis-based token blacklisting
- Session management
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import secrets
import hashlib

from app.core.config import settings
from app.core.redis import RedisManager


# Token expiration times
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Token types
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


class TokenManager:
    """Manages JWT token creation, validation, and lifecycle"""

    def __init__(self, redis_manager: Optional[RedisManager] = None):
        self.redis_manager = redis_manager
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"

    def create_access_token(
        self,
        user_id: str,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create JWT access token (15 minutes expiry).

        Args:
            user_id: User identifier
            additional_claims: Additional JWT claims

        Returns:
            JWT access token string
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        claims = {
            "sub": user_id,  # Subject (user ID)
            "type": TOKEN_TYPE_ACCESS,
            "iat": now,  # Issued at
            "exp": expires_at,  # Expiration
            "jti": self._generate_jti(),  # JWT ID (unique identifier)
        }

        # Add additional claims if provided
        if additional_claims:
            claims.update(additional_claims)

        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        return token

    def create_refresh_token(
        self,
        user_id: str,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create JWT refresh token (7 days expiry).

        Args:
            user_id: User identifier
            additional_claims: Additional JWT claims

        Returns:
            JWT refresh token string
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        claims = {
            "sub": user_id,
            "type": TOKEN_TYPE_REFRESH,
            "iat": now,
            "exp": expires_at,
            "jti": self._generate_jti(),
        }

        if additional_claims:
            claims.update(additional_claims)

        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        return token

    def create_token_pair(
        self,
        user_id: str,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Create both access and refresh tokens.

        Args:
            user_id: User identifier
            additional_claims: Additional JWT claims

        Returns:
            Dict with access_token and refresh_token
        """
        access_token = self.create_access_token(user_id, additional_claims)
        refresh_token = self.create_refresh_token(user_id, additional_claims)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
        }

    def verify_token(
        self,
        token: str,
        expected_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string
            expected_type: Expected token type (access or refresh)

        Returns:
            Decoded token claims

        Raises:
            InvalidTokenError: If token is invalid
            ExpiredSignatureError: If token is expired
        """
        try:
            # Decode and verify token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )

            # Check token type if specified
            if expected_type and payload.get("type") != expected_type:
                raise InvalidTokenError(f"Invalid token type: expected {expected_type}")

            # Check if token is blacklisted (revoked)
            if self.redis_manager:
                jti = payload.get("jti")
                if jti and await self.is_token_blacklisted(jti):
                    raise InvalidTokenError("Token has been revoked")

            return payload

        except ExpiredSignatureError:
            raise ExpiredSignatureError("Token has expired")
        except InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Create new access token from valid refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dict with new access_token

        Raises:
            InvalidTokenError: If refresh token is invalid
        """
        # Verify refresh token
        payload = self.verify_token(refresh_token, expected_type=TOKEN_TYPE_REFRESH)
        user_id = payload.get("sub")

        if not user_id:
            raise InvalidTokenError("Invalid token payload")

        # Create new access token
        access_token = self.create_access_token(user_id)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke (blacklist) a token.

        Args:
            token: JWT token to revoke

        Returns:
            Success status
        """
        if not self.redis_manager:
            return False

        try:
            # Decode token to get jti and exp
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},  # Don't verify expiration
            )

            jti = payload.get("jti")
            exp = payload.get("exp")

            if not jti or not exp:
                return False

            # Calculate TTL (time until expiration)
            exp_datetime = datetime.fromtimestamp(exp)
            ttl_seconds = int((exp_datetime - datetime.utcnow()).total_seconds())

            if ttl_seconds > 0:
                # Add to blacklist with TTL
                key = f"token:blacklist:{jti}"
                await self.redis_manager.set(key, "revoked", ttl_seconds)
                return True

            return False

        except Exception as e:
            print(f"Error revoking token: {e}")
            return False

    async def is_token_blacklisted(self, jti: str) -> bool:
        """
        Check if token is blacklisted.

        Args:
            jti: JWT ID

        Returns:
            True if blacklisted, False otherwise
        """
        if not self.redis_manager:
            return False

        key = f"token:blacklist:{jti}"
        value = await self.redis_manager.get(key)
        return value is not None

    async def revoke_all_user_tokens(self, user_id: str) -> bool:
        """
        Revoke all tokens for a user (logout from all devices).

        Args:
            user_id: User identifier

        Returns:
            Success status
        """
        if not self.redis_manager:
            return False

        try:
            # Add user to revoked list with 7 days TTL (max refresh token lifetime)
            key = f"user:revoked:{user_id}"
            ttl_seconds = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
            await self.redis_manager.set(key, datetime.utcnow().isoformat(), ttl_seconds)
            return True

        except Exception as e:
            print(f"Error revoking user tokens: {e}")
            return False

    async def is_user_revoked(self, user_id: str, token_iat: datetime) -> bool:
        """
        Check if user has been revoked after token was issued.

        Args:
            user_id: User identifier
            token_iat: Token issued at time

        Returns:
            True if user was revoked after token issuance
        """
        if not self.redis_manager:
            return False

        key = f"user:revoked:{user_id}"
        revoked_at = await self.redis_manager.get(key)

        if not revoked_at:
            return False

        try:
            revoked_datetime = datetime.fromisoformat(revoked_at)
            return revoked_datetime > token_iat
        except Exception:
            return False

    def _generate_jti(self) -> str:
        """Generate unique JWT ID"""
        random_bytes = secrets.token_bytes(32)
        return hashlib.sha256(random_bytes).hexdigest()

    def get_user_id_from_token(self, token: str) -> Optional[str]:
        """
        Extract user ID from token without full verification.
        Use only for non-critical operations.

        Args:
            token: JWT token

        Returns:
            User ID or None
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},
            )
            return payload.get("sub")
        except Exception:
            return None


# Session management utilities
class SessionManager:
    """Manages user sessions in Redis"""

    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        self.session_ttl = 7 * 24 * 60 * 60  # 7 days

    async def create_session(
        self,
        user_id: str,
        session_data: Dict[str, Any],
    ) -> str:
        """
        Create user session.

        Args:
            user_id: User identifier
            session_data: Session data to store

        Returns:
            Session ID
        """
        session_id = secrets.token_urlsafe(32)
        key = f"session:{session_id}"

        session = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            **session_data,
        }

        await self.redis_manager.set(
            key,
            session,
            self.session_ttl,
        )

        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None
        """
        key = f"session:{session_id}"
        return await self.redis_manager.get(key)

    async def update_session(
        self,
        session_id: str,
        session_data: Dict[str, Any],
    ) -> bool:
        """
        Update session data.

        Args:
            session_id: Session identifier
            session_data: Updated session data

        Returns:
            Success status
        """
        key = f"session:{session_id}"
        existing = await self.get_session(session_id)

        if not existing:
            return False

        updated = {**existing, **session_data}
        await self.redis_manager.set(key, updated, self.session_ttl)
        return True

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session.

        Args:
            session_id: Session identifier

        Returns:
            Success status
        """
        key = f"session:{session_id}"
        return await self.redis_manager.delete(key)

    async def refresh_session(self, session_id: str) -> bool:
        """
        Refresh session TTL.

        Args:
            session_id: Session identifier

        Returns:
            Success status
        """
        key = f"session:{session_id}"
        exists = await self.redis_manager.client.exists(key)

        if exists:
            await self.redis_manager.client.expire(key, self.session_ttl)
            return True

        return False


# Password utilities
def hash_password(password: str) -> str:
    """
    Hash password using PBKDF2-SHA256.

    Args:
        password: Plain text password

    Returns:
        Hashed password with salt
    """
    import hashlib
    import os

    # Generate random salt
    salt = os.urandom(32)

    # Hash password with PBKDF2-SHA256 (100,000 iterations)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100000,
    )

    # Return salt + hash as hex string
    return salt.hex() + pwd_hash.hex()


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify password against hash.

    Args:
        password: Plain text password
        password_hash: Stored password hash

    Returns:
        True if password matches
    """
    import hashlib

    # Extract salt (first 64 chars = 32 bytes)
    salt = bytes.fromhex(password_hash[:64])
    stored_hash = password_hash[64:]

    # Hash provided password with same salt
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100000,
    )

    # Compare hashes
    return pwd_hash.hex() == stored_hash
