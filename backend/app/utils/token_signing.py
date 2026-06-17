"""T-087: Token signing utilities for export link generation and validation.

Provides cryptographically signed tokens for time-limited file downloads.
Uses itsdangerous.URLSafeTimedSerializer for signing with automatic expiry.
"""

from __future__ import annotations

import uuid

from itsdangerous import URLSafeTimedSerializer


class ExportLinkTokenSigner:
    """Manages signed tokens for export download links.

    Tokens contain the share_id and are cryptographically signed.
    They automatically expire based on the max_age parameter.
    """

    def __init__(self, secret_key: str):
        """Initialize token signer with secret key.

        Args:
            secret_key: Secret key for signing (typically from app config)
        """
        self.serializer = URLSafeTimedSerializer(secret_key)

    def generate_token(
        self,
        share_id: uuid.UUID,
        max_age_seconds: int = 604800,
    ) -> str:
        """Generate a signed token for a share.

        Args:
            share_id: UUID of the ExportShare this link belongs to
            max_age_seconds: How long token is valid (default 7 days)

        Returns:
            URL-safe signed token string
        """
        return self.serializer.dumps({"share_id": str(share_id)})

    def validate_token(
        self,
        token: str,
        max_age_seconds: int = 604800,
    ) -> dict:
        """Validate and decode a signed token.

        Args:
            token: The token to validate
            max_age_seconds: Maximum age of token in seconds

        Returns:
            Dict with decoded data (including share_id)

        Raises:
            SignatureExpired: If token is older than max_age_seconds
            BadSignature: If token signature is invalid or tampered
        """
        return self.serializer.loads(token, max_age=max_age_seconds)

    def extract_share_id(
        self,
        token: str,
        max_age_seconds: int = 604800,
    ) -> uuid.UUID:
        """Extract and validate share_id from token.

        Args:
            token: The token to decode
            max_age_seconds: Maximum age of token in seconds

        Returns:
            The UUID of the ExportShare

        Raises:
            SignatureExpired: If token is expired
            BadSignature: If token is invalid
            ValueError: If share_id is invalid UUID format
        """
        data = self.validate_token(token, max_age_seconds)
        return uuid.UUID(data["share_id"])
