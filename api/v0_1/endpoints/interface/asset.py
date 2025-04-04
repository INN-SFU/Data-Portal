import os
from fastapi import Request, Depends, APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from treelib import node

from core.connectivity import agents

from api.v0_1.endpoints.service.auth import decode_token
from api.v0_1.endpoints.utils.server import convert_file_tree_to_dict


asset_ui_router = APIRouter(prefix='/assets')
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


@asset_ui_router.get("/upload", response_class=HTMLResponse)
def upload_form(request: Request, token_payload: dict = Depends(decode_token)):
    """
    Render the upload form page.
    """
    uid = token_payload.get("preferred_username")

    # Get all storage access points the user has read access to.
    access_points = set([policy[1] for policy in pm.get_user_policies(uid)])
    assets = dict.fromkeys(access_points)

    for agent_slug in access_points:
        def node_filter(n: node):
            vals = (uid, agent_slug, n.identifier, 'write')
            return pm.enforcer.enforce(*vals)

        assets[agents[agent_slug].access_point_slug] = convert_file_tree_to_dict(
            agents[agent_slug].filter_file_tree(node_filter)
        )

    return templates.TemplateResponse("/assets/upload.html", {"request": request, "assets": assets})


@asset_ui_router.get("/download", response_class=HTMLResponse)
def download_form(request: Request, token_payload: dict = Depends(decode_token)):
    """
    Render the download form page.
    """
    uid = token_payload.get("preferred_username")

    # Get all storage access points the user has read access to.
    access_points = set([policy[1] for policy in pm.get_user_policies(uid)])
    assets = dict.fromkeys(access_points)

    for agent_slug in access_points:
        def node_filter(n: node):
            vals = (uid, agent_slug, n.identifier, 'read')
            return pm.enforcer.enforce(*vals)

        assets[agents[agent_slug].access_point_slug] = convert_file_tree_to_dict(
            agents[agent_slug].filter_file_tree(node_filter)
        )

    return templates.TemplateResponse("/assets/download.html", {"request": request, "assets": assets})


@asset_ui_router.get("", response_class=HTMLResponse)
def retrieve_asset(request: Request, token_payload: dict = Depends(decode_token)):
    """
    Generate presigned URLs for assets and serve an HTML template with these URLs.
    """
    uid = token_payload.get("preferred_username")
    resource = request.query_params.get("resource")
    access_point = request.query_params.get("access_point")

    if pm.validate_policy(uid, access_point, resource, "read"):
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
