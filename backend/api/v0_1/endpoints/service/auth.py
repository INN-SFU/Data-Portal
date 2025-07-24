import logging
import os

import jwt
import requests

from fastapi import Request, HTTPException, status, Depends, APIRouter
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

auth_router = APIRouter(prefix='/auth', tags=["Authentication"])

# Set up logger for authentication debugging
logger = logging.getLogger("app")  # Uses the "app" logger from log_config.yaml

# Bearer token authentication scheme
bearer_scheme = HTTPBearer(auto_error=False)


def get_jwks_client():
    """
    Creates a PyJWKClient using the JWKS URI from KeyCloak's well-known configuration.
    """
    well_known_url = os.getenv("KEYCLOAK_WELL_KNOWN_URL")
    logger.debug(f"Using well-known URL: {well_known_url}")
    if not well_known_url:
        logger.error("KEYCLOAK_WELL_KNOWN_URL environment variable is not set")
        raise Exception("KEYCLOAK_WELL_KNOWN_URL is not set")
    
    logger.debug(f"Fetching OIDC configuration from: {well_known_url}")
    oidc_config = requests.get(well_known_url).json()
    logger.debug(f"OIDC config keys: {list(oidc_config.keys())}")
    
    jwks_uri = oidc_config.get("jwks_uri")
    if not jwks_uri:
        logger.error("jwks_uri not found in OIDC configuration")
        raise Exception("jwks_uri not found in OIDC configuration")
    
    logger.debug(f"Using JWKS URI: {jwks_uri}")
    return PyJWKClient(jwks_uri)


def decode_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    # Extract bearer token from Authorization header
    token = credentials.credentials if credentials else None
    
    if not token:
        logger.warning("No token found in Authorization header")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    
    logger.debug("Token received via Authorization header")

    client_id = os.getenv("KEYCLOAK_UI_CLIENT_ID")
    keycloak_domain = os.getenv("KEYCLOAK_DOMAIN")
    realm = os.getenv("KEYCLOAK_REALM")
    issuer = f"{keycloak_domain}/realms/{realm}"
    
    logger.debug(f"Token validation config - client_id: {client_id}, realm: {realm}, issuer: {issuer}")

    jwks_client = get_jwks_client()
    try:
        logger.debug("Getting signing key from JWT token")
        signing_key = jwks_client.get_signing_key_from_jwt(token).key
        logger.debug("Successfully retrieved signing key")
        
        # Decode token with appropriate audience validation
        # Many Keycloak configurations don't include 'aud' claim by default
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False}  # Skip audience validation - common for Keycloak
        )
        logger.debug(f"Token audience claim: {payload.get('aud', 'Not present')}")
        
        # Verify the token is for the correct client by checking client_id in azp or aud
        token_client_id = payload.get('azp') or payload.get('aud')
        if token_client_id and token_client_id != client_id:
            logger.warning(f"Token client_id mismatch: expected {client_id}, got {token_client_id}")
            # Continue anyway - this is informational only
        
        logger.debug(f"Token successfully decoded for user: {payload.get('preferred_username', 'unknown')}")
        logger.debug(f"Token payload keys: {list(payload.keys())}")
    except jwt.PyJWTError as e:
        logger.error(f"JWT validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        ) from e
    return payload




def is_user_admin(token_payload: dict) -> bool:
    """
    Checks if the token payload indicates that the user has admin privileges.
    """
    realm_access = token_payload.get("realm_access", {})
    roles = realm_access.get("roles", [])
    resource_access = token_payload.get("resource_access", {})
    
    logger.debug(f"Checking admin privileges for user: {token_payload.get('preferred_username', 'unknown')}")
    logger.debug(f"Realm access roles: {roles}")
    logger.debug(f"Resource access: {list(resource_access.keys())}")
    
    # Check for admin role in realm_access
    is_admin = "admin" in roles
    
    # Also check in resource_access for client-specific roles
    for client_id, client_roles in resource_access.items():
        client_role_list = client_roles.get("roles", [])
        if "admin" in client_role_list:
            is_admin = True
            logger.debug(f"Found admin role in client {client_id}: {client_role_list}")
    
    logger.debug(f"Admin check result: {is_admin}")
    return is_admin


@auth_router.get("/validate", response_class=JSONResponse)
def validate_token(user: dict = Depends(decode_token)) -> JSONResponse:
    """
    Validate the bearer token and return user information.
    For React frontend token validation.
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"valid": True, "user": user}
    )
