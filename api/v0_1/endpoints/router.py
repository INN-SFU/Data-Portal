from fastapi import APIRouter

from api.v0_1.endpoints.service.auth import auth_router
from api.v0_1.endpoints.service.asset import asset_router
from api.v0_1.endpoints.service.admin import admin_router

from api.v0_1.endpoints.interface.login import ui_router
from api.v0_1.endpoints.interface.user_ui import user_ui_router
from api.v0_1.endpoints.interface.admin_ui import admin_ui_router


application_router = APIRouter()

# Service routers
application_router.include_router(auth_router)
application_router.include_router(asset_router)
application_router.include_router(admin_router)

# UI routers
ui_router.include_router(
    user_ui_router,
    tags=["User Interface"]
)
ui_router.include_router(
    admin_ui_router,
    tags=["Admin Interface"]
)
application_router.include_router(ui_router)
