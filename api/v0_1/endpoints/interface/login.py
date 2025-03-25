from fastapi import Request, APIRouter
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
import os

ui_router = APIRouter(prefix='/ui')


@ui_router.get("/login", response_class=HTMLResponse)
async def ui_login(request: Request):
    """
    Redirect the user to KeyCloak's login page.
    """
    keycloak_login_url = f"{os.getenv('KEYCLOAK_DOMAIN')}/realms/{os.getenv('KEYCLOAK_REALM')}/protocol/openid-connect/auth" \
                         f"?client_id={os.getenv('KEYCLOAK_CLIENT_ID')}" \
                         f"&redirect_uri={os.getenv('KEYCLOAK_REDIRECT_URI')}" \
                         f"&response_type=code"
    return RedirectResponse(url=keycloak_login_url)


@ui_router.get("/logout", response_class=HTMLResponse)
async def ui_logout(request: Request):
    """
    Redirect the user to KeyCloak's logout page.
    """
    keycloak_logout_url = f"{os.getenv('KEYCLOAK_DOMAIN')}/realms/{os.getenv('KEYCLOAK_REALM')}/protocol/openid-connect/logout" \
                          f"?redirect_uri={os.getenv('KEYCLOAK_REDIRECT_URI')}"
    return RedirectResponse(url=keycloak_logout_url)


@ui_router.get("/home", response_class=HTMLResponse)
async def ui_home(request: Request):
    """
    Render the home page.
    """
    return HTMLResponse(content="Welcome to the home page!")
