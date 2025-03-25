import json
import os

from fastapi import APIRouter, HTTPException, status, Depends, requests
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import HTMLResponse

from core.authentication.keycloak_auth import get_current_user, is_user_admin

auth_router = APIRouter(prefix='/auth')


@auth_router.get("/test", response_class=JSONResponse)
def auth(user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    Authenticate the user using the Keycloak token.
    Returns the token claims if valid.
    """
    # The 'user' dict contains token claims from Keycloak.
    return JSONResponse(status_code=status.HTTP_200_OK, content={"success": "Valid token", "user": user})


@auth_router.get("/login", response_class=JSONResponse)
def login(user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    "Login" endpoint for demonstration.
    In a Keycloak setup, users are redirected to Keycloak's login page.
    Once authenticated, Keycloak returns a token which is validated here.
    """
    # Determine the role based on token claims.
    role = "admin" if is_user_admin(user) else "user"
    return JSONResponse(status_code=status.HTTP_200_OK, content={'uid': user.get("preferred_username"), 'role': role})


@auth_router.get("/token", response_class=JSONResponse)
def get_token(user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    Validate the token.
    If the token is valid, this endpoint returns the token's claims.
    """
    return JSONResponse(status_code=status.HTTP_200_OK, content={"detail": "Valid token", "user": user})


@auth_router.get("/callback", response_class=HTMLResponse)
async def keycloak_callback(request: Request):
    # Retrieve the authorization code from query parameters.
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authorization code.")

    # Build the token endpoint URL using environment variables.
    token_url = f"{os.getenv('KEYCLOAK_DOMAIN')}/realms/{os.getenv('KEYCLOAK_REALM')}/protocol/openid-connect/token"

    # Prepare the data for exchanging the code for tokens.
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": os.getenv("KEYCLOAK_REDIRECT_URI"),
        "client_id": os.getenv("KEYCLOAK_CLIENT_ID"),
    }
    # If your client is confidential, include the client secret.
    client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
    if client_secret:
        data["client_secret"] = client_secret

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    # Exchange the authorization code for tokens.
    token_response = requests.post(token_url, data=data, headers=headers)
    if token_response.status_code != 200:
        raise HTTPException(status_code=token_response.status_code,
                            detail="Failed to exchange code for tokens")

    token_data = token_response.json()

    # In production, you might want to set a secure cookie or session with the tokens.
    # Here, we simply display them.
    pretty_tokens = json.dumps(token_data, indent=2)
    return HTMLResponse(content=f"<h1>Login Successful!</h1><pre>{pretty_tokens}</pre>")