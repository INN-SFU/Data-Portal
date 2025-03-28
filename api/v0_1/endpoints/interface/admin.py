import os
import ast
from fastapi import Request, Depends, APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from treelib import node

from api.v0_1.endpoints.service.auth import get_current_user, is_user_admin
from core.settings.endpoints import storage_endpoints
from core.data_access_manager import dam
from core.connectivity.agents import available_flavours
from api.v0_1.endpoints.utils import convert_file_tree_to_dict
from api.v0_1.endpoints.service.admin import gather_endpoints

admin_ui_router = APIRouter(prefix='/admin')
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


@admin_ui_router.get("/policy-management", response_class=HTMLResponse)
async def policy_management(request: Request, token_payload: dict = Depends(get_current_user)):
    """
    Admin page displaying storage endpoints, their file trees, and a policy creation form.
    Requires the user to be an admin.
    """
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Use the preferred_username from the token as uid
    uid = token_payload.get("preferred_username")
    assets = {}
    # Loop through storage endpoints and apply a node filter
    for endpoint_uid, endpoint in zip(storage_endpoints.keys(), storage_endpoints.values()):
        def node_filter(n: node):
            vals = (uid, endpoint_uid, n.identifier, 'write')
            return dam.enforcer.enforce(*vals)

        assets[endpoint_uid] = convert_file_tree_to_dict(endpoint.filter_file_tree(node_filter))
    return templates.TemplateResponse(
        "/admin/policy_management.html",
        {"request": request, "assets": assets, "endpoints": storage_endpoints}
    )


@admin_ui_router.get("/user-management", response_class=HTMLResponse)
async def user_management(request: Request, token_payload: dict = Depends(get_current_user)):
    """
    View function for user management page.
    Displays a list of all users along with their file trees.
    Requires admin privileges.
    """
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    users = dam.get_all_users()
    user_file_trees = {}

    # Loop through users to build file trees based on write access.
    for uid in users:
        access_points = set([policy[1] for policy in dam.get_user_policies(uid)])
        user_file_trees[uid] = dict.fromkeys(access_points)
        for endpoint in storage_endpoints.keys():
            def node_filter(n: node):
                vals = (uid, endpoint, n.identifier, 'write')
                return dam.enforcer.enforce(*vals)

            user_file_trees[uid][endpoint] = convert_file_tree_to_dict(
                storage_endpoints[endpoint].filter_file_tree(node_filter)
            )
    return templates.TemplateResponse(
        "/admin/user_management.html",
        {"request": request, "users": users, "user_file_trees": user_file_trees, "endpoints": storage_endpoints}
    )


@admin_ui_router.get("/endpoint-management", response_class=HTMLResponse)
async def endpoint_management(request: Request, token_payload: dict = Depends(get_current_user)):
    # 1) Auth check
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    # 2) Get data
    details = gather_endpoints()
    # 3) Render template
    return templates.TemplateResponse(
        "admin/endpoint_management.html",
        {"request": request, "endpoints": details, "flavours": available_flavours}
    )
