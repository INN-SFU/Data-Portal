import os

from fastapi import Request, Depends, APIRouter, HTTPException, status, Query
from fastapi.security import HTTPBasic
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from treelib import node

from core.connectivity import agents
from core.data_access_manager import dam

from api.v0_1.endpoints.utils.server import validate_credentials
from api.v0_1.endpoints.utils.server import convert_file_tree_to_dict

security = HTTPBasic()
user_ui_router = APIRouter(prefix='/user')
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


@user_ui_router.get("/home", response_class=HTMLResponse, dependencies=[Depends(validate_credentials)])
def user_home(request: Request):
    """
    Render the user home page.

    Parameters:
    - **request** (Request): The HTTP request information.

    Returns:
    - **TemplateResponse**: The rendered upload form page.
    """
    return templates.TemplateResponse("/user/home.html", {"request": request})


@user_ui_router.get("/home/upload", response_class=HTMLResponse, dependencies=[Depends(validate_credentials)])
def upload_form(request: Request, uid: str = Depends(validate_credentials)):
    """
    Render the upload form page.

    Parameters:
    - **request** (Request): The HTTP request information.
    - **uid** (str): The User ID from the validated credentials.

    Returns:
    - **TemplateResponse**: The rendered upload form page.
    """
    # Get all storage access points user has read access to
    access_points = set([policy[1] for policy in dam.get_user_policies(uid)])

    assets = dict.fromkeys(access_points)

    # Loop through all storage end points
    for agent_slug in access_points:
        # Filter based on read access
        def node_filter(n: node):
            vals = (uid, agent_slug, n.identifier, 'write')
            return dam.enforcer.enforce(*vals)

        # Add the filtered file tree to the
        assets[agents[agent_slug].access_point_slug] = (
            convert_file_tree_to_dict(agents[agent_slug].filter_file_tree(node_filter)))

    return templates.TemplateResponse("/assets/download.html", {"request": request, "assets": assets})


@user_ui_router.get("/home/download", response_class=HTMLResponse)
def download_form(request: Request, uid: str = Depends(validate_credentials)):
    """
    Render the download form page.

    Parameters:
    - **request** (Request): The HTTP request information.
    - **uid** (str): The User ID of the validated user credentials.

    Returns:
    - **TemplateResponse**: The rendered download form page.
    """
    # Get all storage access points user has read access to
    access_points = set([policy[1] for policy in dam.get_user_policies(uid)])

    assets = dict.fromkeys(access_points)

    # Loop through all storage end points
    for agent_slug in access_points:
        # Filter based on read access
        def node_filter(n: node):
            vals = (uid, agent_slug, n.identifier, 'read')
            return dam.enforcer.enforce(*vals)

        # Add the filtered file tree to the
        assets[agents[agent_slug].access_point_slug] = (
            convert_file_tree_to_dict(agents[agent_slug].filter_file_tree(node_filter)))

    return templates.TemplateResponse("/assets/download.html", {"request": request, "assets": assets})


@user_ui_router.get("", response_class=HTMLResponse)
def retrieve_asset(request: Request, uid: str = Depends(validate_credentials)):
    """
    Generate presigned URLs for assets and serve an HTML template with these URLs.

    Parameters:
    - **request** (Request): The request object containing relevant query parameters.
    - **uid** (str): The User ID of the validated credentials.

    Returns:
    - **TemplateResponse**: HTML template with presigned URLs for the assets.

    Raises:
    - **HTTPException**: If the user does not have read access to the resource.
    """
    resource = request.query_params.get("resource")
    access_point = request.query_params.get("access_point")

    if dam.validate_user_access(uid, access_point, resource, "read"):
        try:
            agent = agents[access_point]
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Access point {access_point} not found.")

        presigned_urls, object_keys = agent.generate_access_links(resource, 'GET', 3600)
        return templates.TemplateResponse("download.html",
                                          {"request": request, "presigned_urls": presigned_urls,
                                           "object_keys": object_keys})
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="User does not have read access to this resource")
