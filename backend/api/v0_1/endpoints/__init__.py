from fastapi import APIRouter

from .service import service_router

application_router = APIRouter(prefix="/api")
application_router.include_router(service_router)
