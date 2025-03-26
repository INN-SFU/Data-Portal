import os

import jwt
import requests

from fastapi import Request, HTTPException, status, Depends, APIRouter
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

auth_router = APIRouter(prefix='/auth')

# Use auto_error=False, so we can fall back to cookies if no header is provided.
bearer_scheme = HTTPBearer(auto_error=False)


def get_jwks_client():
    """
    Creates a PyJWKClient using the JWKS URI from KeyCloak's well-known configuration.
    """
    well_known_url = os.getenv("KEYCLOAK_WELL_KNOWN_URL")
    if not well_known_url:
        raise Exception("KEYCLOAK_WELL_KNOWN_URL is not set")
    oidc_config = requests.get(well_known_url).json()
    jwks_uri = oidc_config.get("jwks_uri")
    if not jwks_uri:
        raise Exception("jwks_uri not found in OIDC configuration")
    return PyJWKClient(jwks_uri)


def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    # Try to get the token from the Authorization header.
    token = credentials.credentials if credentials else None
    # Fall back to the cookie if not found.
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    client_id = os.getenv("KEYCLOAK_UI_CLIENT_ID")
    keycloak_domain = os.getenv("KEYCLOAK_DOMAIN")
    realm = os.getenv("KEYCLOAK_REALM")
    issuer = f"{keycloak_domain}/realms/{realm}"

    jwks_client = get_jwks_client()  # Assumes your get_jwks_client is defined elsewhere.
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=["account", client_id] # Your FastAPI server's address
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        ) from e
    return payload


def is_user_admin(token_payload: dict) -> bool:
    """
    Checks if the token payload indicates that the user has admin privileges.
    """
    roles = token_payload.get("realm_access", {}).get("roles", [])
    return "admin" in roles


@auth_router.get("/test", response_class=JSONResponse)
def auth(user: dict = Depends(get_current_user)) -> JSONResponse:
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
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code."
        )

    token_url = f"{os.getenv('KEYCLOAK_DOMAIN')}/realms/{os.getenv('KEYCLOAK_REALM')}/protocol/openid-connect/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": os.getenv("KEYCLOAK_REDIRECT_URI"),
        "client_id": os.getenv("KEYCLOAK_UI_CLIENT_ID"),
        "client_secret": os.getenv("KEYCLOAK_UI_CLIENT_SECRET")
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_response = requests.post(token_url, data=data, headers=headers)
    if token_response.status_code != 200:
        raise HTTPException(
            status_code=token_response.status_code,
            detail="Failed to exchange code for tokens"
        )

    token_data = token_response.json()

    # Create a redirect response to the home endpoint.
    response = RedirectResponse(url="/interface/home", status_code=status.HTTP_302_FOUND)
    # Set the access token in a cookie.
    response.set_cookie(
        key="access_token",
        value=token_data["access_token"],
        httponly=True,  # Helps prevent XSS
        secure=True,  # Change to True in production (HTTPS required)
        path='/'
    )
    return response
