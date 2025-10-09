"""
Issuer Service Configuration

Loads configuration from environment variables.
Generic configuration for any storage type requiring presigned URLs.
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger('issuer.config')


class IssuerConfig:
    """Configuration for Issuer service."""

    def __init__(self):
        """Load configuration from environment variables."""

        # Service configuration
        self.HOST = os.getenv("ISSUER_HOST", "0.0.0.0")
        self.PORT = int(os.getenv("ISSUER_PORT", "8001"))
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

        # JWT signing configuration
        self.JWT_PRIVATE_KEY_FILE = os.getenv("JWT_PRIVATE_KEY_FILE", "/run/secrets/jwt_private_key")
        self.JWT_ISSUER = os.getenv("JWT_ISSUER", "ams-issuer")
        self.JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "ams-gateway")

        # Default Gateway configuration
        # Note: Actual gateway URL should come from storage instance configuration
        # This is just a fallback for testing
        self.GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway.local:9000")

        # API authentication
        self.API_KEY = os.getenv("ISSUER_API_KEY")
        if not self.API_KEY:
            logger.warning("ISSUER_API_KEY not set - API will be unprotected!")

        # Validate configuration
        self._validate()

    def _validate(self):
        """Validate configuration."""
        errors = []

        if not self.GATEWAY_URL:
            errors.append("GATEWAY_URL is required")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

        logger.info(f"Configuration loaded: host={self.HOST}, port={self.PORT}")

    def should_generate_key(self) -> bool:
        """Check if private key needs to be generated."""
        if not self.JWT_PRIVATE_KEY_FILE:
            return True
        return not Path(self.JWT_PRIVATE_KEY_FILE).exists()


# Global config instance
config = None


def get_config() -> IssuerConfig:
    """Get configuration singleton."""
    global config
    if config is None:
        config = IssuerConfig()
    return config
