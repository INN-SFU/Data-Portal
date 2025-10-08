"""
Issuer Service - Server Entry Point

Generic JWT token issuer for storage access.
Issues presigned tokens for any storage type requiring JWT-based authentication.
"""
import os
import sys
import logging
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config
from jwt_handler import JWTSigner, JWKSProvider
from api.v1 import presign_router
from api.v1.presign import init_presign_endpoint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('storage-issuer.server')


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    :return: Configured FastAPI app
    """
    # Load configuration
    config = get_config()

    # Set log level
    logging.getLogger().setLevel(config.LOG_LEVEL)

    # Create FastAPI app
    app = FastAPI(
        title="AMS Storage Issuer Service",
        description="Generic JWT token issuer for storage access with presigned URLs",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # CORS middleware (for development)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize JWT signer
    logger.info("Initializing JWT signer...")

    # Check if we need to generate or load key
    if config.should_generate_key():
        logger.warning("No private key found, generating new RSA key pair")
        jwt_signer = JWTSigner(
            private_key_path=None,
            issuer=config.JWT_ISSUER,
            audience=config.JWT_AUDIENCE
        )

        # Save generated key if path is configured
        if config.JWT_PRIVATE_KEY_FILE:
            try:
                jwt_signer.save_private_key(config.JWT_PRIVATE_KEY_FILE)
                logger.info(f"Private key saved to {config.JWT_PRIVATE_KEY_FILE}")
            except Exception as e:
                logger.error(f"Failed to save private key: {e}")
    else:
        logger.info(f"Loading private key from {config.JWT_PRIVATE_KEY_FILE}")
        jwt_signer = JWTSigner(
            private_key_path=config.JWT_PRIVATE_KEY_FILE,
            issuer=config.JWT_ISSUER,
            audience=config.JWT_AUDIENCE
        )

    # Initialize JWKS provider
    jwks_provider = JWKSProvider(
        public_key=jwt_signer.public_key,
        key_id="default"
    )

    # Initialize presign endpoint with dependencies
    init_presign_endpoint(
        jwt_signer=jwt_signer,
        gateway_url=config.GATEWAY_URL,
        api_key=config.API_KEY
    )

    # Register API routes
    app.include_router(presign_router)

    # JWKS endpoint (public - no auth required)
    @app.get("/.well-known/jwks.json", tags=["jwks"])
    async def get_jwks():
        """
        Get JWKS (JSON Web Key Set) for public key distribution.

        Gateway services use this endpoint to fetch the public key
        for validating JWT tokens.

        This endpoint is public and requires no authentication.
        """
        return jwks_provider.get_jwks()

    # Root endpoint
    @app.get("/", tags=["info"])
    async def root():
        """Service information."""
        return {
            "service": "AMS Storage Issuer Service",
            "description": "Generic JWT token issuer for storage access",
            "version": "1.0.0",
            "issuer": config.JWT_ISSUER,
            "audience": config.JWT_AUDIENCE,
            "jwks_endpoint": "/.well-known/jwks.json"
        }

    logger.info("Storage Issuer service initialized successfully")
    return app


def main():
    """Run the Storage Issuer service."""
    config = get_config()

    logger.info(f"Starting Storage Issuer service on {config.HOST}:{config.PORT}")
    logger.info(f"JWT Issuer: {config.JWT_ISSUER}")
    logger.info(f"JWT Audience: {config.JWT_AUDIENCE}")
    logger.info(f"Gateway URL: {config.GATEWAY_URL}")

    # Create app
    app = create_app()

    # Run server
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()
