"""
Data Encryption and PII Protection Utilities

Implements:
- AES-256 encryption for sensitive data
- PII (Personally Identifiable Information) masking
- Secure hashing
- HIPAA/GDPR compliance utilities
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
import hashlib
import re
from typing import Optional, Dict, Any
import json

from app.core.config import settings


class EncryptionManager:
    """Manages AES-256 encryption and decryption"""

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize encryption manager.

        Args:
            secret_key: Secret key for encryption (uses settings.SECRET_KEY if not provided)
        """
        self.secret_key = secret_key or settings.SECRET_KEY
        self.fernet = self._create_fernet_key()

    def _create_fernet_key(self) -> Fernet:
        """
        Create Fernet cipher using PBKDF2 key derivation.

        Returns:
            Fernet cipher instance
        """
        # Use PBKDF2 to derive a key from the secret
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"aicounselor_salt_2024",  # Static salt (store separately in production)
            iterations=100000,
            backend=default_backend(),
        )

        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key.encode()))
        return Fernet(key)

    def encrypt(self, data: str) -> str:
        """
        Encrypt string data using AES-256.

        Args:
            data: Plain text data

        Returns:
            Encrypted data (base64 encoded)
        """
        if not data:
            return ""

        encrypted = self.fernet.encrypt(data.encode())
        return encrypted.decode()

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt AES-256 encrypted data.

        Args:
            encrypted_data: Encrypted data (base64 encoded)

        Returns:
            Decrypted plain text

        Raises:
            Exception: If decryption fails
        """
        if not encrypted_data:
            return ""

        try:
            decrypted = self.fernet.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            raise Exception(f"Decryption failed: {str(e)}")

    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """
        Encrypt dictionary data.

        Args:
            data: Dictionary to encrypt

        Returns:
            Encrypted JSON string
        """
        json_str = json.dumps(data)
        return self.encrypt(json_str)

    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt dictionary data.

        Args:
            encrypted_data: Encrypted JSON string

        Returns:
            Decrypted dictionary
        """
        json_str = self.decrypt(encrypted_data)
        return json.loads(json_str)


class PIIMasker:
    """Masks Personally Identifiable Information (PII)"""

    @staticmethod
    def mask_email(email: str) -> str:
        """
        Mask email address.

        Example: john.doe@example.com -> j***@example.com

        Args:
            email: Email address

        Returns:
            Masked email
        """
        if not email or "@" not in email:
            return email

        local, domain = email.split("@", 1)

        if len(local) <= 1:
            masked_local = "*"
        else:
            masked_local = local[0] + "***"

        return f"{masked_local}@{domain}"

    @staticmethod
    def mask_phone(phone: str) -> str:
        """
        Mask phone number.

        Example: 010-1234-5678 -> 010-****-5678

        Args:
            phone: Phone number

        Returns:
            Masked phone number
        """
        if not phone:
            return phone

        # Remove non-digit characters
        digits = re.sub(r"\D", "", phone)

        if len(digits) < 4:
            return "****"

        # Mask middle digits
        if len(digits) == 10:
            return f"{digits[:3]}-****-{digits[-4:]}"
        elif len(digits) == 11:
            return f"{digits[:3]}-****-{digits[-4:]}"
        else:
            # Generic masking
            return f"{digits[:2]}****{digits[-2:]}"

    @staticmethod
    def mask_name(name: str) -> str:
        """
        Mask person's name.

        Example: 홍길동 -> 홍**

        Args:
            name: Person's name

        Returns:
            Masked name
        """
        if not name:
            return name

        if len(name) <= 1:
            return "*"

        # Korean name: mask all but first character
        return name[0] + "*" * (len(name) - 1)

    @staticmethod
    def mask_id_number(id_number: str) -> str:
        """
        Mask ID number (주민등록번호, etc.).

        Example: 123456-1234567 -> 123456-1******

        Args:
            id_number: ID number

        Returns:
            Masked ID number
        """
        if not id_number:
            return id_number

        # Korean resident registration number format
        if "-" in id_number:
            parts = id_number.split("-", 1)
            if len(parts) == 2:
                return f"{parts[0]}-{parts[1][0]}******"

        # Generic masking
        if len(id_number) > 6:
            return id_number[:6] + "*" * (len(id_number) - 6)

        return "******"

    @staticmethod
    def mask_credit_card(card_number: str) -> str:
        """
        Mask credit card number.

        Example: 1234-5678-9012-3456 -> 1234-****-****-3456

        Args:
            card_number: Credit card number

        Returns:
            Masked card number
        """
        if not card_number:
            return card_number

        # Remove non-digit characters
        digits = re.sub(r"\D", "", card_number)

        if len(digits) < 8:
            return "****-****-****-****"

        # Show first 4 and last 4 digits
        return f"{digits[:4]}-****-****-{digits[-4:]}"

    @staticmethod
    def mask_ip_address(ip: str) -> str:
        """
        Mask IP address.

        Example: 192.168.1.100 -> 192.168.***.***

        Args:
            ip: IP address

        Returns:
            Masked IP address
        """
        if not ip:
            return ip

        # IPv4
        if "." in ip:
            parts = ip.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.***. ***"

        # IPv6 (simplified)
        if ":" in ip:
            parts = ip.split(":")
            if len(parts) > 2:
                return f"{parts[0]}:{parts[1]}:****:****"

        return "***.***.***. ***"

    @staticmethod
    def mask_text_pii(text: str) -> str:
        """
        Automatically detect and mask PII in text.

        Masks:
        - Email addresses
        - Phone numbers (Korean format)
        - Credit card numbers

        Args:
            text: Text containing potential PII

        Returns:
            Text with masked PII
        """
        if not text:
            return text

        # Mask emails
        text = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            lambda m: PIIMasker.mask_email(m.group(0)),
            text,
        )

        # Mask Korean phone numbers (010-xxxx-xxxx, 02-xxxx-xxxx, etc.)
        text = re.sub(
            r"\b\d{2,3}-\d{3,4}-\d{4}\b",
            lambda m: PIIMasker.mask_phone(m.group(0)),
            text,
        )

        # Mask credit card numbers (xxxx-xxxx-xxxx-xxxx)
        text = re.sub(
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            lambda m: PIIMasker.mask_credit_card(m.group(0)),
            text,
        )

        return text


class SecureHasher:
    """Provides secure hashing utilities"""

    @staticmethod
    def hash_sha256(data: str) -> str:
        """
        Hash data using SHA-256.

        Args:
            data: Data to hash

        Returns:
            SHA-256 hash (hex string)
        """
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def hash_sha512(data: str) -> str:
        """
        Hash data using SHA-512.

        Args:
            data: Data to hash

        Returns:
            SHA-512 hash (hex string)
        """
        return hashlib.sha512(data.encode()).hexdigest()

    @staticmethod
    def hash_with_salt(data: str, salt: str) -> str:
        """
        Hash data with salt using SHA-256.

        Args:
            data: Data to hash
            salt: Salt value

        Returns:
            Salted hash
        """
        combined = f"{data}{salt}"
        return hashlib.sha256(combined.encode()).hexdigest()

    @staticmethod
    def verify_hash(data: str, hash_value: str, salt: Optional[str] = None) -> bool:
        """
        Verify data against hash.

        Args:
            data: Original data
            hash_value: Hash to verify against
            salt: Optional salt value

        Returns:
            True if hash matches
        """
        if salt:
            computed_hash = SecureHasher.hash_with_salt(data, salt)
        else:
            computed_hash = SecureHasher.hash_sha256(data)

        return computed_hash == hash_value


class DataMinimizer:
    """GDPR/HIPAA data minimization utilities"""

    @staticmethod
    def anonymize_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize user data for logging/analytics.

        Args:
            user_data: User data dictionary

        Returns:
            Anonymized user data
        """
        anonymized = user_data.copy()

        # Hash user ID
        if "id" in anonymized:
            anonymized["id"] = SecureHasher.hash_sha256(str(anonymized["id"]))

        # Mask email
        if "email" in anonymized:
            anonymized["email"] = PIIMasker.mask_email(anonymized["email"])

        # Mask name
        if "name" in anonymized:
            anonymized["name"] = PIIMasker.mask_name(anonymized["name"])

        # Mask phone
        if "phone" in anonymized:
            anonymized["phone"] = PIIMasker.mask_phone(anonymized["phone"])

        # Remove sensitive fields
        sensitive_fields = [
            "password",
            "password_hash",
            "session_token",
            "refresh_token",
            "access_token",
            "credit_card",
            "ssn",
            "id_number",
        ]

        for field in sensitive_fields:
            if field in anonymized:
                del anonymized[field]

        return anonymized

    @staticmethod
    def prepare_for_deletion(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare user data for GDPR right-to-be-forgotten compliance.

        Args:
            user_data: User data dictionary

        Returns:
            Sanitized user data (retains only essential audit info)
        """
        return {
            "id": user_data.get("id"),
            "deleted_at": user_data.get("deleted_at"),
            "deletion_reason": "user_request",
            "anonymized": True,
        }

    @staticmethod
    def sanitize_conversation_for_export(conversation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize conversation data for GDPR data export.

        Args:
            conversation: Conversation data

        Returns:
            Sanitized conversation (removes server-side metadata)
        """
        sanitized = conversation.copy()

        # Remove internal fields
        internal_fields = [
            "embedding",
            "internal_notes",
            "flagged_for_review",
            "model_version",
            "processing_time",
            "cache_hit",
        ]

        for field in internal_fields:
            if field in sanitized:
                del sanitized[field]

        return sanitized


# Global instances
encryption_manager = EncryptionManager()
pii_masker = PIIMasker()
secure_hasher = SecureHasher()
data_minimizer = DataMinimizer()
