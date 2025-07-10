from fastapi import APIRouter

from .home import home_router
from .admin import admin_ui_router
from .asset import asset_ui_router

interface_router = APIRouter(prefix="/interface", tags=["Interface"])

interface_router.include_router(home_router)
interface_router.include_router(admin_ui_router)
interface_router.include_router(asset_ui_router)
