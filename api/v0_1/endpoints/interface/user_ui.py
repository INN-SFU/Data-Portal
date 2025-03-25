import os
from fastapi import Request, Depends, APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from treelib import node

from core.connectivity import agents
from core.data_access_manager import dam
from core.settings.endpoints import storage_endpoints
from core.authentication.keycloak_auth import get_current_user
from api.v0_1.endpoints.utils.server import convert_file_tree_to_dict


user_ui_router = APIRouter(prefix='/user')
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


@user_ui_router.get("/home", response_class=HTMLResponse)
async def user_home(request: Request, token_payload: dict = Depends(get_current_user)):
    """
    Render the user home page.
    """
    # Extract the uid from token claims (e.g. "preferred_username")
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
        "/user/home.html",
        {"request": request, "assets": user_file_tree, "endpoints": storage_endpoints}
    )


@user_ui_router.get("/home/upload", response_class=HTMLResponse)
def upload_form(request: Request, token_payload: dict = Depends(get_current_user)):
    """
    Render the upload form page.
    """
    uid = token_payload.get("preferred_username")

    # Get all storage access points the user has read access to.
    access_points = set([policy[1] for policy in dam.get_user_policies(uid)])
    assets = dict.fromkeys(access_points)

    for agent_slug in access_points:
        def node_filter(n: node):
            vals = (uid, agent_slug, n.identifier, 'write')
            return dam.enforcer.enforce(*vals)

        assets[agents[agent_slug].access_point_slug] = convert_file_tree_to_dict(
            agents[agent_slug].filter_file_tree(node_filter)
        )

    return templates.TemplateResponse("/assets/upload.html", {"request": request, "assets": assets})


@user_ui_router.get("/home/download", response_class=HTMLResponse)
def download_form(request: Request, token_payload: dict = Depends(get_current_user)):
    """
    Render the download form page.
    """
    uid = token_payload.get("preferred_username")

    # Get all storage access points the user has read access to.
    access_points = set([policy[1] for policy in dam.get_user_policies(uid)])
    assets = dict.fromkeys(access_points)

    for agent_slug in access_points:
        def node_filter(n: node):
            vals = (uid, agent_slug, n.identifier, 'read')
            return dam.enforcer.enforce(*vals)

        assets[agents[agent_slug].access_point_slug] = convert_file_tree_to_dict(
            agents[agent_slug].filter_file_tree(node_filter)
        )

    return templates.TemplateResponse("/assets/download.html", {"request": request, "assets": assets})


@user_ui_router.get("", response_class=HTMLResponse)
def retrieve_asset(request: Request, token_payload: dict = Depends(get_current_user)):
    """
    Generate presigned URLs for assets and serve an HTML template with these URLs.
    """
    uid = token_payload.get("preferred_username")
    resource = request.query_params.get("resource")
    access_point = request.query_params.get("access_point")

    if dam.validate_user_access(uid, access_point, resource, "read"):
        try:
            agent = agents[access_point]
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Access point {access_point} not found.")
        presigned_urls, object_keys = agent.generate_access_links(resource, 'GET', 3600)
        return templates.TemplateResponse(
            "download.html",
            {"request": request, "presigned_urls": presigned_urls, "object_keys": object_keys}
        )
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="User does not have read access to this resource")
