"""
Password hashing and verification using Python stdlib only.

Uses hashlib.scrypt with a random per-user salt.
"""
import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    """
    Hash a password with a random salt using scrypt.
    
    Args:
        password: Plaintext password
    
    Returns:
        String in format: salt:hash (hex-encoded)
    """
    # Generate random 16-byte salt
    salt = secrets.token_bytes(16)
    
    # Hash with scrypt (N=16384, r=8, p=1 are recommended parameters)
    password_hash = hashlib.scrypt(
        password.encode('utf-8'),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        dklen=32
    )
    
    # Return salt:hash in hex format
    return f"{salt.hex()}:{password_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify a password against a stored hash (constant-time comparison).
    
    Args:
        password: Plaintext password to verify
        stored_hash: Stored hash in format salt:hash (hex-encoded)
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        # Extract salt and hash
        salt_hex, hash_hex = stored_hash.split(':')
        salt = bytes.fromhex(salt_hex)
        stored_password_hash = bytes.fromhex(hash_hex)
        
        # Hash the provided password with the same salt
        password_hash = hashlib.scrypt(
            password.encode('utf-8'),
            salt=salt,
            n=16384,
            r=8,
            p=1,
            dklen=32
        )
        
        # Constant-time comparison
        return hmac.compare_digest(password_hash, stored_password_hash)
        
    except (ValueError, AttributeError):
        return False
