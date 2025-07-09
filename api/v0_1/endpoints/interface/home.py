from uuid import UUID

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from treelib import node

from api.v0_1.endpoints.dependencies import get_policy_manager, get_endpoint_manager, get_user_manager

from api.v0_1.endpoints.utils.server import convert_file_tree_to_dict

from api.v0_1.templates import templates
from api.v0_1.endpoints.service.auth import decode_token, is_user_admin
from core.management.policies import AbstractPolicyManager
from core.management.endpoints import AbstractEndpointManager

home_router = APIRouter(prefix="/home", tags=["Home UI"])


@home_router.get("", response_class=HTMLResponse)
async def home(request: Request,
               token_payload: dict = Depends(decode_token),
               policy_manager=Depends(get_policy_manager),
               endpoint_manager=Depends(get_endpoint_manager)):
    import logging
    logger = logging.getLogger("app")
    
    user = token_payload.get("preferred_username", "unknown")
    logger.info(f"Home page accessed by user: {user}")
    
    if is_user_admin(token_payload):
        logger.info(f"Serving admin home template for user: {user}")
        return templates.TemplateResponse("admin/home.html", {"request": request})
    else:
        logger.info(f"Serving user home template for user: {user}")
        uid = token_payload.get("preferred_username")

        # Get all storage access points the user has read access to.

        access_points = set([policy[1] for policy in policy_manager.get_user_policies(uid)])
        user_file_tree = dict.fromkeys(access_points)

        # Loop through each storage endpoint and filter its file tree.
        storage_endpoints = endpoint_manager.get_endpoints(access_points)
        for endpoint in storage_endpoints.keys():
            def node_filter(n: node):
                vals = (uid, endpoint, n.identifier, 'write')
                return policy_manager.enforcer.enforce(*vals)

            user_file_tree[endpoint] = convert_file_tree_to_dict(
                storage_endpoints[endpoint].filter_file_tree(node_filter)
            )

        return templates.TemplateResponse(
            "user/home.html",
            {"request": request, "assets": user_file_tree, "endpoints": storage_endpoints}
        )


@home_router.get("/assets", response_class=HTMLResponse)
async def assets_home(request: Request,
                      token_payload: dict = Depends(decode_token),
                      policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                      endpoint_manager: AbstractEndpointManager = Depends(get_endpoint_manager)):

    # Retrieve the user's user_uuid from the token payload.
    uuid = token_payload.get("sub")

    # Get all storage access points the user has read access to.
    endpoint_point_uids = set([UUID(policy[1]) for policy in policy_manager.get_user_policies(uuid)])
    endpoints = endpoint_manager.get_endpoint(endpoint_point_uids)

    file_trees = {}

    # Loop through each storage endpoint and filter its file tree.
    for uid, agent in endpoints.items():
        def node_filter(n: node):
            vals = (uuid, uid.__str__(), n.identifier, '*')
            return policy_manager.validate_policy(*vals)

        file_trees[uid.__str__()] = convert_file_tree_to_dict(agent.filter_file_tree(node_filter) )

    access_point_names = {endpoint.access_point_name: uid.__str__() for uid, endpoint in endpoints.items()}

    return templates.TemplateResponse(
        "user/home.html",
        {"request": request, "assets": file_trees, 'endpoints': access_point_names}
    )

