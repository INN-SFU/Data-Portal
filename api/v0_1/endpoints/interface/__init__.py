import os
from urllib.parse import urlencode

from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse

from .home import home_router
from .admin import admin_ui_router
from .asset import asset_ui_router

interface_router = APIRouter(prefix="/interface", tags=["Interface"])

interface_router.include_router(home_router)
interface_router.include_router(admin_ui_router)
interface_router.include_router(asset_ui_router)

@interface_router.get("/logout", response_model=None)
async def ui_logout(response: Response):
    """
    Logout user by clearing authentication cookies and redirecting to Keycloak logout.
    
    This endpoint performs a complete logout by:
    1. Clearing the JWT authentication cookie from the browser
    2. Redirecting to Keycloak's logout endpoint to terminate the SSO session
    3. Keycloak will redirect back to the application after logout
    """
    # Clear the JWT token cookie
    response.delete_cookie(
        key="access_token",
        path="/",
        domain=None,
        secure=False,  # Set to True in production with HTTPS
        httponly=True,
        samesite="lax"
    )
    
    # Build Keycloak logout URL with proper parameters
    # For logout, redirect to the landing page
    base_url = os.getenv('KEYCLOAK_REDIRECT_URI', 'http://localhost:8000').split('/auth/callback')[0]
    logout_params = {
        "redirect_uri": f"{base_url}/",
        "client_id": os.getenv('KEYCLOAK_UI_CLIENT_ID', 'ams-portal-ui')
    }
    
    keycloak_logout_url = (
        f"{os.getenv('KEYCLOAK_DOMAIN')}/realms/{os.getenv('KEYCLOAK_REALM')}/protocol/openid-connect/logout"
        f"?{urlencode(logout_params)}"
    )
    
    return RedirectResponse(url=keycloak_logout_url, status_code=302)
