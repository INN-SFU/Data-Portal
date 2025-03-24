import os
import ast

from fastapi import Request, Depends, APIRouter
from fastapi.security import HTTPBasic
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from treelib import node

from core.settings.endpoints import storage_endpoints
from core.data_access_manager import dam
from core.connectivity.agents import available_flavours

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
    for endpoint_uid, endpoint in zip(storage_endpoints.keys(), storage_endpoints.values()):
        # Filter based on write access for the admin. Write access allows admin to update policies.
        def node_filter(n: node):
            vals = (uid, endpoint_uid, n.identifier, 'write')
            return dam.enforcer.enforce(*vals)

        # Apply the filter
        assets[endpoint_uid] = convert_file_tree_to_dict(endpoint.filter_file_tree(node_filter))
    return templates.TemplateResponse("/admin/policy_management.html", {"request": request, "assets": assets,
                                                                        "endpoints": storage_endpoints})


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
        for endpoint in storage_endpoints.keys():
            # Filter based on read and write access
            def node_filter(n: node):
                vals = (uid, endpoint, n.identifier, 'write')
                return dam.enforcer.enforce(*vals)

            # Apply the filter
            user_file_trees[uid][endpoint] = convert_file_tree_to_dict(
                storage_endpoints[endpoint].filter_file_tree(node_filter))

    return templates.TemplateResponse("/admin/user_management.html",
                                      {"request": request, "users": users,
                                       "user_file_trees": user_file_trees,
                                       "endpoints": storage_endpoints})


@admin_ui_router.get("/home/endpoint-management", response_class=HTMLResponse, dependencies=[Depends(is_admin)])
async def endpoint_management(request: Request):
    """
    View function for endpoint_url management page.

    Parameters:
    - **request** (Request): The HTTP request object.

    Returns:
    - **TemplateResponse**: The response object with endpoint_url management page.
    """
    response = await list_endpoints()
    content = ast.literal_eval(response.body.decode('utf-8'))
    return templates.TemplateResponse("/admin/endpoint_management.html", {"request": request,
                                                                          "endpoints": content['endpoints'],
                                                                          "flavours": available_flavours})
