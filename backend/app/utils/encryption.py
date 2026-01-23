# ===========================================
# AuraTask - Field Encryption Utility
# ===========================================
# Uses Fernet symmetric encryption (AES-128-CBC with HMAC)
# for encrypting sensitive user data at rest.

from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def get_fernet() -> Optional[Fernet]:
    """
    Get Fernet instance if ENCRYPTION_KEY is configured.
    
    Returns:
        Fernet instance or None if encryption is not configured
    """
    if not settings.ENCRYPTION_KEY:
        return None
    try:
        return Fernet(settings.ENCRYPTION_KEY.encode())
    except Exception as e:
        print(f"[ENCRYPTION] Invalid ENCRYPTION_KEY: {e}")
        return None


def encrypt_field(value: Optional[str]) -> Optional[str]:
    """
    Encrypt a string field for storage in database.
    
    Args:
        value: Plain text value to encrypt
        
    Returns:
        Encrypted value (base64 encoded) or original value if encryption disabled
    """
    if value is None:
        return None
    
    fernet = get_fernet()
    if fernet is None:
        # No encryption in development or if key not set
        return value
    
    try:
        encrypted = fernet.encrypt(value.encode())
        return encrypted.decode()
    except Exception as e:
        print(f"[ENCRYPTION] Encrypt error: {e}")
        return value


def decrypt_field(value: Optional[str]) -> Optional[str]:
    """
    Decrypt a string field from database.
    
    Args:
        value: Encrypted value (base64 encoded)
        
    Returns:
        Decrypted plain text value or original value if decryption fails
    """
    if value is None:
        return None
    
    fernet = get_fernet()
    if fernet is None:
        # No encryption configured, return as-is
        return value
    
    try:
        decrypted = fernet.decrypt(value.encode())
        return decrypted.decode()
    except InvalidToken:
        # Value might be unencrypted (legacy data), return as-is
        return value
    except Exception as e:
        print(f"[ENCRYPTION] Decrypt error: {e}")
        return value
