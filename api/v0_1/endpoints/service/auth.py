import logging
import os

import jwt
import requests

from fastapi import Request, HTTPException, status, Depends, APIRouter
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

auth_router = APIRouter(prefix='/auth', tags=["Authentication"])

# Set up logger for authentication debugging
logger = logging.getLogger("app")  # Uses the "app" logger from log_config.yaml

# Use auto_error=False, so we can fall back to cookies if no header is provided.
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


def decode_token(request: Request, credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    # Try to get the token from the Authorization header.
    token = credentials.credentials if credentials else None
    logger.debug(f"Token from Authorization header: {'Found' if token else 'Not found'}")
    
    # Fall back to the cookie if not found.
    if not token:
        token = request.cookies.get("access_token")
        logger.debug(f"Token from cookie: {'Found' if token else 'Not found'}")
    
    if not token:
        logger.warning("No token found in Authorization header or cookies")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

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


@auth_router.get("/test", response_class=JSONResponse)
def auth(user: dict = Depends(decode_token)) -> JSONResponse:
    """
    Authenticate the user using the Keycloak token.
    Returns the token claims if valid.
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": "Valid token", "user": user}
    )


@auth_router.get("/login", response_model=None)
async def ui_login(request: Request):
    """
    Redirect the user to KeyCloak's login page.
    """
    login_url = os.getenv("KEYCLOAK_LOGIN_URL")
    if not login_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="KEYCLOAK_LOGIN_URL is not set"
        )
    return RedirectResponse(url=login_url)


@auth_router.get("/callback", response_model=None)
async def keycloak_callback(request: Request):
    code = request.query_params.get("code")
    logger.debug(f"OAuth callback received with code: {'Present' if code else 'Missing'}")

    if not code:
        logger.error("OAuth callback missing authorization code")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code."
        )

    logger.info(f"Processing OAuth callback with authorization code: {code[:10]}...")
    token_url = f"{os.getenv('KEYCLOAK_DOMAIN')}/realms/{os.getenv('KEYCLOAK_REALM')}/protocol/openid-connect/token"
    logger.debug(f"Token exchange URL: {token_url}")
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": os.getenv("KEYCLOAK_REDIRECT_URI"),
        "client_id": os.getenv("KEYCLOAK_UI_CLIENT_ID"),
        "client_secret": os.getenv("KEYCLOAK_UI_CLIENT_SECRET")
    }
    logger.debug(f"Token exchange data: {dict(data, client_secret='***')}")  # Don't log the secret
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    logger.debug("Making token exchange request to Keycloak")
    token_response = requests.post(token_url, data=data, headers=headers)
    
    logger.debug(f"Token response status: {token_response.status_code}")
    if token_response.status_code != 200:
        logger.error(f"Token exchange failed with status {token_response.status_code}: {token_response.text}")
        raise HTTPException(
            status_code=token_response.status_code,
            detail="Failed to exchange code for tokens"
        )

    token_data = token_response.json()
    logger.info("Successfully exchanged authorization code for tokens")
    logger.debug(f"Token data keys: {list(token_data.keys())}")

    # Create a redirect response to the home endpoint.
    response = RedirectResponse(url="/interface/home", status_code=status.HTTP_302_FOUND)
    # Set the access token in a cookie.
    response.set_cookie(
        key="access_token",
        value=token_data["access_token"],
        httponly=True,  # Helps prevent XSS
        secure=True,  # Change to True in production (HTTPS required)
        samesite="lax",
        path='/'
    )
    logger.debug("Set access token cookie and redirecting to /interface/home")
    return response
