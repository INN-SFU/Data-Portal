import os

from fastapi import Request, Depends, APIRouter, HTTPException
from fastapi.security import HTTPBasic
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.connectivity import agents
from core.data_access_manager import dam

from api.v0_1.endpoints.utils.server import validate_credentials
from api.v0_1.endpoints.utils.server import convert_file_tree_to_dict

security = HTTPBasic()
user_ui_router = APIRouter(prefix='/user')
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


# UPLOAD AND DOWNLOAD FORMS
@user_ui_router.get("/upload", response_class=HTMLResponse)
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
    return templates.TemplateResponse("/assets/upload.html", {"request": request, "assets": assets})


# Endpoint to render the download form
@user_ui_router.get("/download", response_class=HTMLResponse)
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
    return templates.TemplateResponse("/assets/download.html", {"request": request, "assets": assets})


@user_ui_router.get("")
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
