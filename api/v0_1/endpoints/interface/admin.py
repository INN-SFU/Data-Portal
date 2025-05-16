import os

from fastapi import Request, Depends, APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from api.v0_1.endpoints.service.auth import decode_token, is_user_admin
from api.v0_1.endpoints.dependencies import get_user_manager, get_policy_manager, get_endpoint_manager

from api.v0_1.endpoints.service.models import model_registry

from core.management.policies import AbstractPolicyManager, Policy
from core.management.users import AbstractUserManager
from core.management.endpoints import AbstractEndpointManager

from core.connectivity.agents import available_flavours
from api.v0_1.endpoints.utils import convert_file_tree_to_dict

admin_ui_router = APIRouter(prefix='/admin', tags=["Admin UI"])
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


@admin_ui_router.get("/policy-management", response_class=HTMLResponse)
async def policy_management(request: Request,
                            token_payload: dict = Depends(decode_token),
                            user_manager: AbstractUserManager = Depends(get_user_manager),
                            policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                            endpoint_manager: AbstractEndpointManager = Depends(get_endpoint_manager)):
    """
    Admin page displaying storage endpoints, their file trees, and a policy creation form.
    Requires the user to be an admin.
    """
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    username = token_payload.get("preferred_username")
    uuid = user_manager.get_user_uuid(username)

    policy = Policy(
        user_uuid=uuid,
        action='admin'
    )

    # Get all endpoints the user has 'admin' access to.
    admin_policies = policy_manager.filter_policies(policy)
    admin_endpoint_uuids = list(set(policy.endpoint_uuid for policy in admin_policies))
    admin_endpoints = endpoint_manager.get_endpoints_by_uuid(admin_endpoint_uuids)

    assets = {}
    # Populate the file trees for each endpoint
    for endpoint in admin_endpoints:
        # Partition the file type based on the policy
        assets[endpoint.name] = convert_file_tree_to_dict(
            endpoint.agent.partition_file_tree_by_access(policy_manager, uuid, endpoint.uuid, 'admin')['admin']
        )

    return templates.TemplateResponse(
        "/admin/policy_management.html",
        {"request": request, "assets": assets, "endpoints": admin_endpoints}
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
        # Get all storage endpoints the user has read access to.
        endpoint_uuids = list(set(policy.endpoint_uuid for policy in policy_manager.get_user_policies(user.uuid)))
        endpoints = endpoint_manager.get_endpoints_by_uuid(endpoint_uuids)

        user_trees = {}

        # Loop through each storage endpoint and filter its file tree.
        for endpoint in endpoints:
            f_trees = endpoint.agent.partition_file_tree_by_access(policy_manager, user.uuid, endpoint.uuid,
                                                                   ['read', 'write', 'admin'])

            if f_trees is not None:
                user_trees[(endpoint.name, endpoint.uuid)] = \
                    {access_type: convert_file_tree_to_dict(tree) for access_type, tree in f_trees.items()}

        file_trees[user.uuid] = user_trees

    # Include the required form metadata for the models
    required_models = [
        "AddUserRequest",
        "AddUserResponse",
        "RemoveUserResponse"
    ]

    json_registry = {
        name: {
            "endpoint": entry["endpoint"],
            "schema": entry["model_class"].model_json_schema()
        }
        for name, entry in model_registry.items()
        if name in required_models
    }

    return templates.TemplateResponse(
        "/admin/user_management.html",
        {"request": request, "users": users, "file_trees": file_trees, "models": json_registry}
    )


@admin_ui_router.get("/endpoint-management", response_class=HTMLResponse)
async def endpoint_management(request: Request,
                              token_payload: dict = Depends(decode_token),
                              endpoint_manager: AbstractEndpointManager = Depends(get_endpoint_manager)):
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Gather endpoint details
    endpoints = endpoint_manager.endpoints

    configs = {
        endpoint.name: (endpoint.uuid.__str__(), endpoint.config(secrets=False))
        for endpoint in endpoints
    }

    # Render template
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

    # Retrieve the user's user_uuid from the token payload.
    uuid = token_payload.get("sub")

    # Get all storage access points the user has read access to.
    endpoint_uuids = list(
        set(policy.endpoint_uuid for policy in policy_manager.get_user_policies(uuid))
    )
    endpoints = endpoint_manager.get_endpoints_by_uuid(endpoint_uuids)

    file_trees = {}
    for endpoint in endpoints:
        f_trees = endpoint.agent.partition_file_tree_by_access(
            policy_manager, uuid, endpoint.uuid, ["read", "write"]
        )
        if f_trees is not None:
            file_trees[str(endpoint.uuid)] = {
                access_type: convert_file_tree_to_dict(tree)
                for access_type, tree in f_trees.items()
            }

    # **Convert to simple string → string mapping** so Jinja can JSON‐encode it:
    endpoint_names = {endpoint.name: str(endpoint.uuid) for endpoint in endpoints}

    return templates.TemplateResponse(
        "admin/asset_management.html",
        {
            "request": request,
            "assets": file_trees,
            "endpoints": endpoint_names,   # now both keys & values are plain strings
        },
    )