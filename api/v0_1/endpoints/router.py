from fastapi import APIRouter

from api.v0_1.endpoints.service.auth import auth_router
from api.v0_1.endpoints.service.user import user_router
from api.v0_1.endpoints.service.admin import admin_router

from api.v0_1.endpoints.interface.user import user_ui_router
from api.v0_1.endpoints.interface.admin import admin_ui_router


application_router = APIRouter()

application_router.include_router(auth_router, prefix='/service')
application_router.include_router(user_router, prefix='/service')
application_router.include_router(admin_router, prefix='/service')

application_router.include_router(user_ui_router)
application_router.include_router(admin_ui_router)
