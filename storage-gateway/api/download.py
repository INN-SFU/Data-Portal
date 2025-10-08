"""
Download API Endpoint

Main endpoint for downloading files using JWT tokens.
Validates tokens and streams files from POSIX filesystem.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import Response

logger = logging.getLogger('storage-gateway.api.download')

# Dependencies (initialized by server.py)
_jwt_validator = None
_jti_tracker = None
_file_streamer = None
_manifest_generator = None
_zip_streamer = None


def init_download_endpoint(
    jwt_validator,
    jti_tracker,
    file_streamer,
    manifest_generator,
    zip_streamer
):
    """
    Initialize download endpoint with dependencies.

    Called by server.py during startup.
    """
    global _jwt_validator, _jti_tracker, _file_streamer, _manifest_generator, _zip_streamer

    _jwt_validator = jwt_validator
    _jti_tracker = jti_tracker
    _file_streamer = file_streamer
    _manifest_generator = manifest_generator
    _zip_streamer = zip_streamer

    logger.info("Download endpoint initialized with dependencies")


# Create router
router = APIRouter(prefix="/api", tags=["download"])


@router.get("/download")
async def download(
    request: Request,
    token: str = Query(..., description="JWT token from Storage Issuer")
) -> Response:
    """
    Download file or folder using JWT token.

    **Token Claims:**
    - `path`: Resource path (locked to this specific path)
    - `op`: Operation (must be "read")
    - `bundle`: Download type - "file" (single file), "manifest" (JSON list), "zip" (ZIP archive)
    - `jti`: Token ID (for single-use enforcement)
    - `cip` (optional): Client IP (for IP pinning)

    **Response Types:**
    - **bundle=file**: Stream file with HTTP Range support (or FileResponse)
    - **bundle=manifest**: JSON listing of folder contents
    - **bundle=zip**: ZIP archive of folder (streamed on-the-fly)

    **Security:**
    - Validates JWT signature using Issuer's public key
    - Checks expiration, audience, issuer
    - Enforces single-use via Redis jti tracking
    - Validates client IP if token has IP pinning
    - Validates path to prevent directory traversal
    - Checks operation is "read" (write not supported on download endpoint)

    :param request: FastAPI request (for getting client IP)
    :param token: JWT token string
    :return: File content, manifest JSON, or ZIP archive
    """
    try:
        # 1. Validate JWT token
        logger.info("Validating JWT token")
        claims = _jwt_validator.validate_token(token)

        # Extract claims
        jti = claims["jti"]
        path = claims["path"]
        operation = claims["op"]
        bundle = claims.get("bundle", "file")  # Default to "file" for consistency with frontend
        user_uuid = claims.get("sub")
        ttl = claims["exp"] - claims["iat"]

        logger.info(
            f"Token validated",
            extra={
                "jti": jti,
                "user": user_uuid,
                "path": path,
                "op": operation,
                "bundle": bundle
            }
        )

        # 2. Validate operation (must be "read" for download)
        if operation != "read":
            logger.error(f"Invalid operation for download: {operation}")
            raise HTTPException(
                status_code=403,
                detail=f"Invalid operation: {operation} (must be 'read' for download)"
            )

        # 3. Validate client IP if token has IP pinning
        client_ip = request.client.host if request.client else None
        if client_ip:
            _jwt_validator.validate_client_ip(claims, client_ip)

        # 4. Check jti (single-use enforcement)
        logger.info(f"Checking jti for replay: {jti}")
        _jti_tracker.check_and_mark_used(
            jti=jti,
            ttl=ttl,
            metadata={
                "user_uuid": user_uuid,
                "path": path,
                "operation": operation,
                "client_ip": client_ip
            }
        )

        # 5. Stream file/folder based on bundle type
        if bundle == "file":
            # Stream single file (with HTTP Range support)
            range_header = request.headers.get("Range")
            logger.info(f"Streaming file: {path} (range: {range_header or 'none'})")
            return _file_streamer.stream_file(path, range_header)

        elif bundle == "manifest":
            # Generate JSON manifest of folder
            logger.info(f"Generating manifest: {path}")
            return _manifest_generator.generate_manifest(path, recursive=False)

        elif bundle == "zip":
            # Stream folder as ZIP archive
            logger.info(f"Streaming ZIP archive: {path}")
            return _zip_streamer.stream_zip(path)

        else:
            logger.error(f"Invalid bundle type: {bundle}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid bundle type: {bundle} (must be 'file', 'manifest', or 'zip')"
            )

    except HTTPException:
        # Re-raise FastAPI HTTP exceptions
        raise

    except Exception as e:
        # Log and return generic error
        logger.error(f"Download failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Download failed: {str(e)}"
        )


@router.get("/health")
async def health():
    """
    Health check endpoint.

    Checks:
    - JWT validator initialized
    - Redis connection healthy
    - File streamer initialized

    :return: Health status
    """
    checks = {
        "jwt_validator": _jwt_validator is not None,
        "jti_tracker": _jti_tracker is not None and _jti_tracker.health_check(),
        "file_streamer": _file_streamer is not None,
        "manifest_generator": _manifest_generator is not None,
        "zip_streamer": _zip_streamer is not None
    }

    all_healthy = all(checks.values())

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "checks": checks
    }
