from fastapi import APIRouter

from .service import service_router
from .interface import interface_router

application_router = APIRouter()
application_router.include_router(service_router)
application_router.include_router(interface_router)
