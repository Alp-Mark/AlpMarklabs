"""Password hashing and verification utilities using bcrypt."""

import bcrypt


def hash_password(plain_password: str) -> str:
    """Hash a plain text password using bcrypt.
    
    Args:
        plain_password: The plain text password to hash
        
    Returns:
        The bcrypt hashed password as a string
    """
    password_bytes = plain_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hashed password.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hashed password to check against
        
    Returns:
        True if the password matches, False otherwise
    """
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)
