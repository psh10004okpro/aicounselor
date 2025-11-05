"""Encryption utilities for sensitive data"""

import hashlib
import secrets
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

from app.core.config import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""

    def __init__(self, secret_key: str = None):
        """
        Initialize encryption service.

        Args:
            secret_key: Base secret key (uses settings.SECRET_KEY if not provided)
        """
        self.secret_key = secret_key or settings.SECRET_KEY

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from secret using PBKDF2"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(self.secret_key.encode())

    def encrypt(self, data: str) -> str:
        """
        Encrypt data using Fernet (symmetric encryption).

        Returns:
            Encrypted data as base64 string with salt prefix
        """
        if not data:
            return ""

        # Generate random salt
        salt = secrets.token_bytes(16)

        # Derive key from secret + salt
        key = self._derive_key(salt)

        # Create Fernet instance
        f = Fernet(Fernet.generate_key())  # Using Fernet's key generation

        # Encrypt data
        encrypted = f.encrypt(data.encode())

        # Return salt + encrypted data (both base64 encoded)
        import base64

        salt_b64 = base64.b64encode(salt).decode()
        encrypted_b64 = base64.b64encode(encrypted).decode()

        return f"{salt_b64}:{encrypted_b64}"

    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """
        Decrypt data.

        Args:
            encrypted_data: Encrypted data with salt prefix

        Returns:
            Decrypted string or None if decryption fails
        """
        if not encrypted_data:
            return None

        try:
            import base64

            # Split salt and encrypted data
            parts = encrypted_data.split(":")
            if len(parts) != 2:
                return None

            salt_b64, encrypted_b64 = parts

            # Decode from base64
            salt = base64.b64decode(salt_b64)
            encrypted = base64.b64decode(encrypted_b64)

            # Derive key
            key = self._derive_key(salt)

            # Create Fernet instance
            f = Fernet(key)

            # Decrypt
            decrypted = f.decrypt(encrypted)

            return decrypted.decode()

        except Exception as e:
            print(f"Decryption error: {e}")
            return None

    def hash_email(self, email: str) -> str:
        """
        Hash email for indexing (SHA-256).

        This allows searching by email without storing plaintext.
        """
        return hashlib.sha256(email.lower().encode()).hexdigest()

    def encrypt_email(self, email: str) -> tuple[str, str]:
        """
        Encrypt email and generate hash.

        Returns:
            Tuple of (encrypted_email, email_hash)
        """
        encrypted = self.encrypt(email)
        email_hash = self.hash_email(email)
        return encrypted, email_hash

    def generate_session_token(self) -> str:
        """Generate secure random session token"""
        return secrets.token_urlsafe(32)

    def generate_api_key(self) -> str:
        """Generate API key"""
        return f"sk-{secrets.token_urlsafe(32)}"

    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt.

        Note: In production, use passlib or bcrypt library directly
        """
        import bcrypt

        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)
        return hashed.decode()

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        import bcrypt

        return bcrypt.checkpw(password.encode(), hashed.encode())


# Global encryption service instance
encryption_service = EncryptionService()
