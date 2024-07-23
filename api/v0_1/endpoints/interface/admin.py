import os

from fastapi import Request, Depends, HTTPException, APIRouter
from fastapi.security import HTTPBasic
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.connectivity import agents
from core.data_access_manager import dam

from api.v0_1.endpoints.utils import convert_file_tree_to_dict
from api.v0_1.endpoints.utils.server import is_admin

security = HTTPBasic()
admin_ui_router = APIRouter(prefix='/admin')
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


# Admin Home Page
@admin_ui_router.get("/home")
async def admin_home(request: Request, uid: str = Depends(is_admin)):
    return templates.TemplateResponse("/admin/home.html", {"request": request})


@admin_ui_router.get("/home/asset-management", response_class=HTMLResponse, dependencies=[Depends(is_admin)])
async def admin_management(request: Request, uid: str = Depends(is_admin)):
    """
    Admin home page that displays the storage endpoints and file trees.

    :param request: The HTTP request object containing information about the incoming request.
    :param uid: The unique identifier of the admin user.
    :return: The HTML response containing the admin management interface.
    """
    assets = {}
    for agent in agents:
        assets[agent.access_point_slug] = convert_file_tree_to_dict(agent.get_user_file_tree(uid, 'write', dam))
    return templates.TemplateResponse("/admin/assets.html", {"request": request, "assets": assets})


# Endpoint to display users and their file access
@admin_ui_router.get("/home/user-management", response_class=HTMLResponse, dependencies=[Depends(is_admin)])
async def user_management(request: Request):
    """
    View function for user access page.

    :param request: The HTTP request object.
    :return: The response object with user access page.
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
