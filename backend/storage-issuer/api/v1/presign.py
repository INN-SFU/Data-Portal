"""
Presign API Endpoint

Generates presigned JWT tokens for file access.
Backend calls this endpoint after validating user authentication and authorization.
"""
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Header, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, Literal

logger = logging.getLogger('issuer.api.presign')

router = APIRouter(prefix="/v1", tags=["presign"])


# Request/Response Models
class PresignRequest(BaseModel):
    """Request to generate a presigned token."""
    user_uuid: str = Field(..., description="User UUID (already validated by Backend)")
    instance_uuid: str = Field(..., description="Storage instance UUID")
    path: str = Field(..., description="Resource path (relative to storage root)")
    op: Literal["read", "write"] = Field(..., description="Operation type")
    ttl: int = Field(default=3600, ge=60, le=86400, description="Time-to-live in seconds (60s to 24h)")
    bundle: Literal["file", "manifest", "zip"] = Field(default="file", description="Download bundle type")
    client_ip: Optional[str] = Field(default=None, description="Optional client IP for token pinning")


class PresignResponse(BaseModel):
    """Response containing presigned token."""
    token: str = Field(..., description="Signed JWT token")
    expires_at: str = Field(..., description="Token expiration timestamp (ISO 8601)")
    download_url: str = Field(..., description="Full URL for downloading with token")


# Global instances (initialized by server.py)
_jwt_signer = None
_gateway_url = None
_api_key = None


def init_presign_endpoint(jwt_signer, gateway_url: str, api_key: str):
    """
    Initialize the presign endpoint with dependencies.

    Called by server.py during startup.

    :param jwt_signer: JWTSigner instance
    :param gateway_url: Gateway service URL
    :param api_key: API key for authentication
    """
    global _jwt_signer, _gateway_url, _api_key
    _jwt_signer = jwt_signer
    _gateway_url = gateway_url.rstrip('/')
    _api_key = api_key
    logger.info("Presign endpoint initialized")


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """
    Verify API key from request header.

    :param x_api_key: API key from X-API-Key header
    :raises HTTPException: If API key is invalid
    """
    if not _api_key:
        logger.error("API key not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured"
        )

    if x_api_key != _api_key:
        logger.warning("Invalid API key attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )


@router.post("/presign", response_model=PresignResponse)
async def presign(
    request: PresignRequest,
    _: None = Depends(verify_api_key)
):
    """
    Generate a presigned JWT token for file access.

    **Authentication**: Requires valid API key in X-API-Key header.

    **Authorization**: Backend must have already validated user permissions.

    **Flow**:
    1. User authenticates with Backend (Keycloak token)
    2. Backend checks Casbin policy for resource access
    3. Backend calls this endpoint with user_uuid and approved path
    4. Issuer signs JWT token with path locked in
    5. Backend returns token to user
    6. User presents token to Gateway for file download

    **Token Security**:
    - Signed with RS256 (private key on Issuer)
    - Gateway validates with public key (from JWKS endpoint)
    - Token locks user to specific path and operation
    - Single-use enforcement via jti in Redis (Gateway side)
    - Time-limited (TTL)

    :param request: Presign request
    :return: Presigned token response
    """
    # Check signer is initialized
    if not _jwt_signer:
        logger.error("JWT signer not initialized")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT signer not initialized"
        )

    try:
        # Sign JWT token
        token = _jwt_signer.sign_token(
            path=request.path,
            operation=request.op,
            subject=request.user_uuid,
            ttl=request.ttl,
            bundle=request.bundle,
            client_ip=request.client_ip,
            instance_uuid=request.instance_uuid
        )

        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=request.ttl)

        # Build download URL (points to Gateway on storage server)
        download_url = f"{_gateway_url}/api/download?token={token}"

        logger.info(
            f"Presigned token issued: user={request.user_uuid}, "
            f"instance={request.instance_uuid}, path={request.path}, op={request.op}"
        )

        return PresignResponse(
            token=token,
            expires_at=expires_at.isoformat(),
            download_url=download_url
        )

    except Exception as e:
        logger.error(f"Failed to sign token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sign token: {str(e)}"
        )


@router.get("/health")
async def health():
    """
    Health check endpoint.

    :return: Service health status
    """
    return {
        "status": "healthy",
        "service": "ams-posix-issuer",
        "signer_initialized": _jwt_signer is not None
    }
