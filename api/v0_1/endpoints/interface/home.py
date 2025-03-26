import os

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from treelib import node

from api.v0_1.endpoints.utils.server import convert_file_tree_to_dict
from api.v0_1.templates import templates
from api.v0_1.endpoints.service.auth import get_current_user, is_user_admin
from core.data_access_manager import dam
from core.settings.endpoints import storage_endpoints

home_router = APIRouter(prefix="/home")


@home_router.get("", response_class=HTMLResponse)
async def home(request: Request, token_payload: dict = Depends(get_current_user)):
    if is_user_admin(token_payload):
        return templates.TemplateResponse("admin/home.html", {"request": request})
    else:
        uid = token_payload.get("preferred_username")

        # Get all storage access points the user has read access to.
        access_points = set([policy[1] for policy in dam.get_user_policies(uid)])
        user_file_tree = dict.fromkeys(access_points)

        # Loop through each storage endpoint and filter its file tree.
        for endpoint in storage_endpoints.keys():
            def node_filter(n: node):
                vals = (uid, endpoint, n.identifier, 'write')
                return dam.enforcer.enforce(*vals)

            user_file_tree[endpoint] = convert_file_tree_to_dict(
                storage_endpoints[endpoint].filter_file_tree(node_filter)
            )

        return templates.TemplateResponse(
            "user/home.html",
            {"request": request, "assets": user_file_tree, "endpoints": storage_endpoints}
        )


@home_router.get("/assets", response_class=HTMLResponse)
async def assets_home(request: Request, token_payload: dict = Depends(get_current_user)):
    uid = token_payload.get("preferred_username")

    # Get all storage access points the user has read access to.
    access_points = set([policy[1] for policy in dam.get_user_policies(uid)])
    user_file_tree = dict.fromkeys(access_points)

    # Loop through each storage endpoint and filter its file tree.
    for endpoint in storage_endpoints.keys():
        def node_filter(n: node):
            vals = (uid, endpoint, n.identifier, 'write')
            return dam.enforcer.enforce(*vals)

        user_file_tree[endpoint] = convert_file_tree_to_dict(
            storage_endpoints[endpoint].filter_file_tree(node_filter)
        )

    return templates.TemplateResponse(
        "user/home.html",
        {"request": request, "assets": user_file_tree, "endpoints": storage_endpoints}
    )

