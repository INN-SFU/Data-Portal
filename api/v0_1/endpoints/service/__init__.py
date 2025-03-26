from fastapi import APIRouter

from api.v0_1.endpoints.service.auth import auth_router
from api.v0_1.endpoints.service.asset import asset_router
from api.v0_1.endpoints.service.admin import admin_router

service_router = APIRouter()

# Service routers
service_router.include_router(auth_router)
service_router.include_router(asset_router)
service_router.include_router(admin_router)

