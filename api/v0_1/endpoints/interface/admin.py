import os
from uuid import UUID

from fastapi import Request, Depends, APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from treelib import node

from api.v0_1.endpoints.service.auth import decode_token, is_user_admin
from api.v0_1.endpoints.dependencies import get_user_manager, get_policy_manager, get_endpoint_manager

from core.management.policies import AbstractPolicyManager
from core.management.users import AbstractUserManager
from core.management.endpoints import AbstractEndpointManager

from core.connectivity.agents import available_flavours
from api.v0_1.endpoints.utils import convert_file_tree_to_dict

admin_ui_router = APIRouter(prefix='/admin')
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


@admin_ui_router.get("/policy-management", response_class=HTMLResponse)
async def policy_management(request: Request,
                            token_payload: dict = Depends(decode_token),
                            policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                            endpoint_manager: AbstractEndpointManager = Depends(get_endpoint_manager)):
    """
    Admin page displaying storage endpoints, their file trees, and a policy creation form.
    Requires the user to be an admin.
    """
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Use the preferred_username from the token as uid
    uuid = token_payload.get("sub")

    # Get all endpoints the user has 'admin' access to.
    admin_policies = policy_manager.filter_policies(uuid, None, 'admin')
    admin_endpoint_uids = set(map(UUID, admin_policies.keys()))
    admin_endpoints = endpoint_manager.get_endpoint(admin_endpoint_uids)

    assets = {}
    access_point_names = {endpoint.access_point_slug: uid.__str__() for uid, endpoint in admin_endpoints.items()}
    # Populate the file trees for each endpoint
    for uid, agent in admin_endpoints.items():
        assets[agent.access_point_slug] = convert_file_tree_to_dict(
            agent.partition_file_tree_by_access(policy_manager, uuid, uid, 'admin')['admin']
        )

    return templates.TemplateResponse(
        "/admin/policy_management.html",
        {"request": request, "assets": assets, "endpoints": access_point_names}
    )


@admin_ui_router.get("/user-management", response_class=HTMLResponse)
async def user_management(request: Request,
                          token_payload: dict = Depends(decode_token),
                          user_manager: AbstractUserManager = Depends(get_user_manager),
                          policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                          endpoint_manager: AbstractEndpointManager = Depends(get_endpoint_manager)):
    """
    View function for user management page.
    Displays a list of all users along with their file trees.
    Requires admin privileges.
    """
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    users = user_manager.get_all_users()
    file_trees = {}

    # Loop through users to build file trees based on write access.
    for user in users:
        uuid = user['id']

        # Get all storage access points the user has read access to.
        endpoint_uids = set([UUID(policy[1]) for policy in policy_manager.get_user_policies(uuid)])
        endpoints = endpoint_manager.get_endpoint(endpoint_uids)

        user_trees = {}

        # Loop through each storage endpoint and filter its file tree.
        for uid, agent in endpoints.items():
            def node_filter(n: node):
                vals = (uuid, uid.__str__(), n.identifier, '*')
                return policy_manager.validate_policy(*vals)

            user_trees[uid.__str__()] = convert_file_tree_to_dict(agent.filter_file_tree(node_filter))

        access_point_names = {endpoint.access_point_slug: uid.__str__() for uid, endpoint in endpoints.items()}
        file_trees[uuid] = user_trees

    return templates.TemplateResponse(
        "/admin/user_management.html",
        {"request": request, "users": users, "file_trees": file_trees}
    )


@admin_ui_router.get("/endpoint-management", response_class=HTMLResponse)
async def endpoint_management(request: Request,
                              token_payload: dict = Depends(decode_token),
                              endpoint_manager: AbstractEndpointManager = Depends(get_endpoint_manager)):
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Gather endpoint details
    endpoints = endpoint_manager.get_endpoints()

    configs = {
        endpoint.access_point_slug: (str(uid), endpoint.get_config())
        for uid, endpoint in endpoints.items()
    }

    # 3) Render template
    return templates.TemplateResponse(
        "admin/endpoint_management.html",
        {"request": request, "endpoints": configs, "flavours": available_flavours}
    )


@admin_ui_router.get("/asset-management", response_class=HTMLResponse)
async def assets_management(request: Request,
                            token_payload: dict = Depends(decode_token),
                            policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                            endpoint_manager: AbstractEndpointManager = Depends(get_endpoint_manager)):
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Retrieve the user's uuid from the token payload.
    uuid = token_payload.get("sub")

    # Get all storage access points the user has read access to.
    endpoint_uids = set([UUID(policy[1]) for policy in policy_manager.get_user_policies(uuid)])
    endpoints = endpoint_manager.get_endpoint(endpoint_uids)

    file_trees = {}

    # Loop through each storage endpoint and filter its file tree based on access types
    for uid, agent in endpoints.items():
        def node_filter(n: node):
            vals = (uuid, uid.__str__(), n.identifier, 'read')
            return policy_manager.validate_policy(*vals)

        f_trees = agent.partition_file_tree_by_access(policy_manager, uuid, uid, ['read', 'write'])
        file_trees[uid.__str__()] = {access_type: convert_file_tree_to_dict(tree) for access_type, tree in f_trees.items()}


    access_point_names = {endpoint.access_point_slug: uid.__str__() for uid, endpoint in endpoints.items()}

    return templates.TemplateResponse(
        "admin/asset_management.html",
        {"request": request, "assets": file_trees, 'endpoints': access_point_names}
    )
