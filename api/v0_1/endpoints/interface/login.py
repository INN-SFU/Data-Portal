import json
import os

from fastapi import Request, Depends, APIRouter
from fastapi.security import HTTPBasic
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from api.v0_1.endpoints.service.auth import login as service_login
from api.v0_1.endpoints.interface.admin import admin_home
from api.v0_1.endpoints.interface.user import user_home

security = HTTPBasic()
ui_router = APIRouter(prefix='/ui')
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


@ui_router.get("/login", response_class=HTMLResponse)
async def ui_login(
    request: Request,
    service_data: dict = Depends(service_login)
):
    """
    Process the login by relying on the service login endpoint (HTTP Basic).
    If valid, redirect to the appropriate home page based on the user's role.
    """
    service_data = json.loads(service_data.body)
    role = service_data.get("role")
    if role == "admin":
        return await admin_home(request)
    elif role == "user":
        return await user_home(request)
    else:
        # In case the role is unrecognized.
        return HTMLResponse(content="Unknown user role", status_code=400)


@ui_router.get("/logout", response_class=HTMLResponse)
async def ui_logout(request: Request):
    return HTMLResponse(content="Not implemented", status_code=501)