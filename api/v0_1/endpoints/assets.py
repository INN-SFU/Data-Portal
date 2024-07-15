import os
import logging
from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from treelib import Tree

from core.authentication import auth
from core.settings.config import dam
from core.settings.config import agents

security = HTTPBasic()
asset_router = APIRouter(prefix='/assets')

templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))

logger = logging.getLogger("uvicorn")


# UTILITES/HELPER FUNCTIONS
def convert_file_tree_to_dict(tree: Tree):
    tree_data = []
    for node in tree.all_nodes():
        if node.tag != 'root':  # Skip the 'root' node
            parent = tree.parent(node.identifier)
            # If the parent is 'root', treat this node as a top-level node
            parent_id = '#' if parent is None or parent.tag == 'root' else parent.identifier
            tree_data.append(
                {"id": node.identifier, "parent": parent_id, "text": node.tag, "li_attr": {"data-id": node.identifier}}
            )
    return tree_data


# ENDPOINT ACCESS CONTROL
def validate_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    uid = credentials.username
    password = credentials.password

    if uid not in dam.get_users():
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if auth.validate_credentials(uid, password):
        return uid, password
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


# GENERAL AND USER ENDPOINTS
@asset_router.get("/list")
def read_assets(creds: str = Depends(validate_credentials)):
    """
    Retrieves assets for a user.

    :return: The assets for the user.
    :raises HTTPException: If the provided credentials are invalid.
    :rtype: dict
    """
    uid = creds[0]

    # Retrieve assets for user_id
    assets = dam.get_all_user_assets(uid)

    # Valid Response
    return {"assets": assets}


@asset_router.get("")
def retrieve_asset(request: Request, creds: str = Depends(validate_credentials)):
    """
    This method is used to generate presigned URLs for assets and serve an HTML template with these URLs.

    :param request: The request object containing relevant query parameters.
    :param creds: The user ID and key used to validate user credentials.
    :return: HTML template with presigned URLs for the assets.
    :raises HTTPException: If the user does not have read access to the resource.
    """
    uid = creds[0]

    resource = request.query_params.get("resource")
    access_point = request.query_params.get("access_point")

    if dam.validate_user_access(uid, access_point, resource, "read"):
        for agent in agents:
            if agent.access_point_slug == access_point:
                try:
                    presigned_urls, object_keys = agent.generate_access_links(resource, 'GET', 3600)
                    return templates.TemplateResponse("download.html",
                                                      {"request": request, "presigned_urls": presigned_urls,
                                                       "object_keys": object_keys})
                except ValueError as e:
                    raise HTTPException(status_code=404, detail=str(e))
    else:
        raise HTTPException(status_code=403, detail="User does not have read access to this resource")


# UPLOAD AND DOWNLOAD FORMS
@asset_router.get("/upload", response_class=HTMLResponse)
def upload_form(request: Request, creds: str = Depends(validate_credentials)):
    """
    This method is used to render the upload form page.

    :param request: The HTTP request information.
    :type request: Request
    :param creds: The validated user credentials.
    :type creds: str
    :return: The rendered upload form page.
    :rtype: TemplateResponse
    """
    uid = creds[0]
    assets = {}
    for agent in agents:
        assets[agent.access_point_slug] = convert_file_tree_to_dict(agent.get_user_file_tree(uid, 'write', dam))
    return templates.TemplateResponse("upload.html", {"request": request, "assets": assets})


# Endpoint to render the download form
@asset_router.get("/download", response_class=HTMLResponse)
def download_form(request: Request, creds: str = Depends(validate_credentials)):
    """
    This method is used to render the download form page.
    :param request: The HTTP request information.
    :param creds: The validated user credentials.
    :return: The rendered download form page.
    """
    uid = creds[0]
    assets = {}
    for agent in agents:
        assets[agent.access_point_slug] = convert_file_tree_to_dict(agent.get_user_file_tree(uid, 'read', dam))
    return templates.TemplateResponse("download.html", {"request": request, "assets": assets})


# UPLOAD AND DOWNLOAD PRESIGNED URL ENDPOINTS
@asset_router.put("/upload")
def put_asset(request: Request, creds: str = Depends(validate_credentials)) -> dict:
    """
    Sends a PUT request to the asset router to generate a presigned URL for uploading a file.

    :param request: The request object.
    :type request: Request
    :param creds: The credentials required for authentication.
    :type creds: str
    :return: The presigned URL for uploading the file.
    :rtype: dict
    :raises HTTPException 404: If the asset router URL is not found or the file cannot be uploaded.
    :raises HTTPException 403: If the user does not have write access to the resource.
    """
    uid = creds[0]
    resource = request.query_params.get("resource")
    access_point = request.query_params.get("access_point")

    if dam.validate_user_access(uid, access_point, resource, "write"):
        for agent in agents:
            if agent.access_point_slug == access_point:
                try:
                    presigned_urls, file_paths = agent.generate_access_links(f"{resource}", 'PUT', 3600)
                    return {"presigned_urls": presigned_urls, 'file_paths': file_paths}
                except ValueError as e:
                    raise HTTPException(status_code=404, detail=str(e))
    else:
        raise HTTPException(status_code=403, detail="User does not have write access to this resource")


# Endpoint to generate presigned URLs for downloading assets
@asset_router.put("/download")
def get_asset(request: Request, creds: str = Depends(validate_credentials)) -> dict:
    """
    Get presigned URLs for downloading the specified asset.

    :param request: The request object.
    :type request: Request
    :param creds: The user credentials.
    :type creds: str
    :return: The presigned URLs for the asset.
    :rtype: dict

    :raises HTTPException 404: If the asset is not found.
    :raises HTTPException 403: If the user does not have access to the asset.
    """
    uid = creds[0]
    resource = request.query_params.get("resource")
    access_point = request.query_params.get("access_point")

    if dam.validate_user_access(uid, access_point, resource, "read"):
        for agent in agents:
            if agent.access_point_slug == access_point:
                try:
                    presigned_urls, file_paths = agent.generate_access_links(resource, 'GET', 600)
                    return {"presigned_urls": presigned_urls, 'file_paths': file_paths}
                except ValueError as e:
                    raise HTTPException(status_code=404, detail=str(e))
    else:
        raise HTTPException(status_code=403, detail="User does not have access to the specified resource")
