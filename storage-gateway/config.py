"""
Configuration Module

Loads configuration from environment variables.
"""
import os
import logging
from dataclasses import dataclass

logger = logging.getLogger('storage-gateway.config')


@dataclass
class Config:
    """Storage Gateway configuration."""

    # Server settings
    HOST: str
    PORT: int
    LOG_LEVEL: str

    # Storage settings
    STORAGE_ROOT_PATH: str

    # JWT validation settings
    JWKS_URL: str
    JWT_ISSUER: str
    JWT_AUDIENCE: str
    JWKS_CACHE_TTL: int

    # Redis settings (for jti tracking)
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str | None

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Validate storage root path
        if not os.path.exists(self.STORAGE_ROOT_PATH):
            logger.warning(f"Storage root path does not exist: {self.STORAGE_ROOT_PATH}")

        # Log configuration (without sensitive data)
        logger.info(f"Configuration loaded:")
        logger.info(f"  Server: {self.HOST}:{self.PORT}")
        logger.info(f"  Storage root: {self.STORAGE_ROOT_PATH}")
        logger.info(f"  JWKS URL: {self.JWKS_URL}")
        logger.info(f"  JWT Issuer: {self.JWT_ISSUER}")
        logger.info(f"  JWT Audience: {self.JWT_AUDIENCE}")
        logger.info(f"  Redis: {self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}")


def get_config() -> Config:
    """
    Load configuration from environment variables.

    :return: Config instance
    """
    return Config(
        # Server settings
        HOST=os.getenv("GATEWAY_HOST", "0.0.0.0"),
        PORT=int(os.getenv("GATEWAY_PORT", "9000")),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),

        # Storage settings
        STORAGE_ROOT_PATH=os.getenv(
            "STORAGE_ROOT_PATH",
            "/storage"  # Default path in container
        ),

        # JWT validation settings
        JWKS_URL=os.getenv(
            "JWKS_URL",
            "http://storage-issuer:8001/.well-known/jwks.json"
        ),
        JWT_ISSUER=os.getenv("JWT_ISSUER", "ams-storage-issuer"),
        JWT_AUDIENCE=os.getenv("JWT_AUDIENCE", "ams-storage-gateway"),
        JWKS_CACHE_TTL=int(os.getenv("JWKS_CACHE_TTL", "3600")),

        # Redis settings
        REDIS_HOST=os.getenv("REDIS_HOST", "localhost"),
        REDIS_PORT=int(os.getenv("REDIS_PORT", "6379")),
        REDIS_DB=int(os.getenv("REDIS_DB", "0")),
        REDIS_PASSWORD=os.getenv("REDIS_PASSWORD"),  # Optional
    )
