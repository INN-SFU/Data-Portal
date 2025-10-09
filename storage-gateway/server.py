"""
Storage Gateway - Server Entry Point

Validates JWT tokens and streams files from POSIX filesystem.
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
from auth.jwt_validator import JWTValidator
from auth.jti_tracker import JTITracker
from streaming.file_stream import FileStreamer
from streaming.manifest import ManifestGenerator
from streaming.zip_stream import ZipStreamer
from api.download import router as download_router, init_download_endpoint
from api.tree import router as tree_router, init_tree_endpoint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('storage-gateway.server')


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
        title="AMS Storage Gateway Service",
        description="Validates JWT tokens and streams files from POSIX filesystem",
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

    # Initialize JWT validator
    logger.info("Initializing JWT validator...")
    jwt_validator = JWTValidator(
        jwks_url=config.JWKS_URL,
        audience=config.JWT_AUDIENCE,
        issuer=config.JWT_ISSUER,
        cache_ttl=config.JWKS_CACHE_TTL
    )

    # Initialize JTI tracker (Redis)
    logger.info("Initializing JTI tracker...")
    jti_tracker = JTITracker(
        redis_host=config.REDIS_HOST,
        redis_port=config.REDIS_PORT,
        redis_db=config.REDIS_DB,
        redis_password=config.REDIS_PASSWORD
    )

    # Initialize file streamer
    logger.info("Initializing file streamer...")
    file_streamer = FileStreamer(root_path=config.STORAGE_ROOT_PATH)

    # Initialize manifest generator
    logger.info("Initializing manifest generator...")
    manifest_generator = ManifestGenerator(root_path=config.STORAGE_ROOT_PATH)

    # Initialize ZIP streamer
    logger.info("Initializing ZIP streamer...")
    zip_streamer = ZipStreamer(root_path=config.STORAGE_ROOT_PATH)

    # Initialize download endpoint with dependencies
    init_download_endpoint(
        jwt_validator=jwt_validator,
        jti_tracker=jti_tracker,
        file_streamer=file_streamer,
        manifest_generator=manifest_generator,
        zip_streamer=zip_streamer
    )

    # Initialize tree endpoint
    init_tree_endpoint(root_path=config.STORAGE_ROOT_PATH)

    # Register API routes
    app.include_router(download_router)
    app.include_router(tree_router)

    # Root endpoint
    @app.get("/", tags=["info"])
    async def root():
        """Service information."""
        return {
            "service": "AMS Storage Gateway Service",
            "description": "Validates JWT tokens and streams files from POSIX filesystem",
            "version": "1.0.0",
            "storage_root": config.STORAGE_ROOT_PATH,
            "jwt_issuer": config.JWT_ISSUER,
            "jwt_audience": config.JWT_AUDIENCE
        }

    logger.info("Storage Gateway service initialized successfully")
    return app


def main():
    """Run the Storage Gateway service."""
    config = get_config()

    logger.info(f"Starting Storage Gateway service on {config.HOST}:{config.PORT}")
    logger.info(f"Storage root: {config.STORAGE_ROOT_PATH}")
    logger.info(f"JWKS URL: {config.JWKS_URL}")
    logger.info(f"JWT Issuer: {config.JWT_ISSUER}")
    logger.info(f"JWT Audience: {config.JWT_AUDIENCE}")

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
