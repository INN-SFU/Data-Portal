import os

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from .home import home_router
from .admin import admin_ui_router
from .asset import asset_ui_router

interface_router = APIRouter(prefix="/interface", tags=["Interface"])

interface_router.include_router(home_router)
interface_router.include_router(admin_ui_router)
interface_router.include_router(asset_ui_router)

@interface_router.get("/logout", response_model=None)
async def ui_logout():
    """
    Redirect the user to KeyCloak's logout page.
    """
    keycloak_logout_url = (
        f"{os.getenv('KEYCLOAK_DOMAIN')}/realms/{os.getenv('KEYCLOAK_REALM')}/protocol/openid-connect/logout"
        f"?redirect_uri={os.getenv('KEYCLOAK_REDIRECT_URI')}"
    )
    return RedirectResponse(url=keycloak_logout_url)
