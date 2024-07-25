import os

from fastapi import Request, Depends, APIRouter
from fastapi.security import HTTPBasic
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.connectivity import agents
from core.data_access_manager import dam

from api.v0_1.endpoints.utils import convert_file_tree_to_dict
from api.v0_1.endpoints.utils.server import is_admin, validate_credentials

security = HTTPBasic()
admin_ui_router = APIRouter(prefix='/admin')
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


@admin_ui_router.get("/home", response_class=HTMLResponse, dependencies=[Depends(is_admin)])
async def admin_home(request: Request):
    """
    Admin home page.

    Parameters:
    - **request** (Request): The HTTP request object containing information about the incoming request.

    Returns:
    - **TemplateResponse**: The HTML response containing the admin home page.
    """
    return templates.TemplateResponse("/admin/home.html", {"request": request})


@admin_ui_router.get("/home/policy-management", response_class=HTMLResponse, dependencies=[Depends(is_admin)])
async def policy_management(request: Request, uid: str = Depends(validate_credentials)):
    """
    Admin home page that displays the storage endpoints, their file trees, and policy creation form.

    Parameters:
    - **request** (Request): The HTTP request object containing information about the incoming request.
    - **uid** (str): The unique identifier of the validated admin user.

    Returns:
    - **TemplateResponse**: The HTML response containing the admin management interface.
    """
    assets = {}
    for agent in agents:
        assets[agent.access_point_slug] = convert_file_tree_to_dict(agent.get_user_file_tree(uid, 'write', dam))
    return templates.TemplateResponse("/admin/policy_management.html", {"request": request, "assets": assets})


@admin_ui_router.get("/home/user-management", response_class=HTMLResponse, dependencies=[Depends(is_admin)])
async def user_management(request: Request):
    """
    View function for user access page.

    Parameters:
    - **request** (Request): The HTTP request object.

    Returns:
    - **TemplateResponse**: The response object with user access page.
    """
    users = dam.get_all_users()
    user_file_trees = {}
    for uid in users:
        user_file_trees[uid] = {}
        for agent in agents:
            user_file_trees[uid][agent.access_point_slug] = convert_file_tree_to_dict(
                agent.get_user_file_tree(uid, 'read', dam))
    return templates.TemplateResponse("/admin/user_management.html",
                                      {"request": request, "users": users,
                                       "user_file_trees": user_file_trees})
