import os
import ast

from fastapi import Request, Depends, APIRouter
from fastapi.security import HTTPBasic
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from treelib import node

from core.connectivity import agents
from core.data_access_manager import dam

from api.v0_1.endpoints.utils import convert_file_tree_to_dict
from api.v0_1.endpoints.utils.server import is_admin, validate_credentials

from api.v0_1.endpoints.service.admin import list_endpoints

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
    # Loop through storage endpoints
    for agent in agents.values():
        # Filter based on write access for the admin. Write access allows admin to update policies.
        def node_filter(n: node):
            vals = (uid, agent.access_point_slug, n.identifier, 'write')
            return dam.enforcer.enforce(*vals)

        # Apply the filter
        assets[agent.access_point_slug] = convert_file_tree_to_dict(agent.filter_file_tree(node_filter))
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

    # Loop through users
    for uid in users:
        # Get all storage access points user has read access to
        access_points = set([policy[1] for policy in dam.get_user_policies(uid)])

        user_file_trees[uid] = dict.fromkeys(access_points)

        # Loop through filtered access points
        for agent_slug in agents:
            # Filter based on read and write access
            def node_filter(n: node):
                vals = (uid, agent_slug, n.identifier, 'write')
                return dam.enforcer.enforce(*vals)

            # Apply the filter
            user_file_trees[uid][agent_slug] = convert_file_tree_to_dict(
                agents[agent_slug].filter_file_tree(node_filter))

    return templates.TemplateResponse("/admin/user_management.html",
                                      {"request": request, "users": users,
                                       "user_file_trees": user_file_trees})


@admin_ui_router.get("/home/endpoint-management", response_class=HTMLResponse, dependencies=[Depends(is_admin)])
async def endpoint_management(request: Request):
    """
    View function for endpoint management page.

    Parameters:
    - **request** (Request): The HTTP request object.

    Returns:
    - **TemplateResponse**: The response object with endpoint management page.
    """
    response = await list_endpoints()
    content = ast.literal_eval(response.body.decode('utf-8'))
    return templates.TemplateResponse("/admin/endpoint_management.html", {"request": request,
                                                                          "endpoints": content['endpoints']})
