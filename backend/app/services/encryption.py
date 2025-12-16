"""
Encryption service for sensitive data (Betfair credentials)
Uses Fernet (symmetric encryption) from cryptography library
"""
from cryptography.fernet import Fernet
from app.config import get_settings

settings = get_settings()


class EncryptionService:
    """
    Service for encrypting/decrypting sensitive data
    Uses Fernet symmetric encryption (AES-128 in CBC mode)
    """

    def __init__(self):
        """Initialize encryption service with key from settings"""
        if not settings.encryption_key:
            raise ValueError("ENCRYPTION_KEY not set in environment variables!")

        # Encryption key must be 32 url-safe base64-encoded bytes
        self.cipher = Fernet(settings.encryption_key.encode())

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string

        Args:
            plaintext: String to encrypt

        Returns:
            Encrypted string (base64 encoded)
        """
        if not plaintext:
            return ""

        encrypted_bytes = self.cipher.encrypt(plaintext.encode())
        return encrypted_bytes.decode()

    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt encrypted string

        Args:
            encrypted_text: Encrypted string (base64 encoded)

        Returns:
            Decrypted plaintext string
        """
        if not encrypted_text:
            return ""

        decrypted_bytes = self.cipher.decrypt(encrypted_text.encode())
        return decrypted_bytes.decode()

    def encrypt_dict(self, data: dict) -> dict:
        """
        Encrypt all values in a dictionary

        Args:
            data: Dictionary with string values

        Returns:
            Dictionary with encrypted values
        """
        return {key: self.encrypt(value) for key, value in data.items() if value}

    def decrypt_dict(self, data: dict) -> dict:
        """
        Decrypt all values in a dictionary

        Args:
            data: Dictionary with encrypted values

        Returns:
            Dictionary with decrypted values
        """
        return {key: self.decrypt(value) for key, value in data.items() if value}


# Singleton instance
encryption_service = EncryptionService()
