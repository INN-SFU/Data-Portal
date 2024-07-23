import logging

from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.security import HTTPBasic
from api.v0_1.endpoints.utils.server import validate_credentials

from core.connectivity import agents
from core.data_access_manager import dam

security = HTTPBasic()
user_router = APIRouter(prefix='/user')

logger = logging.getLogger("uvicorn")


# GENERAL AND USER ENDPOINTS
@user_router.get("/list")
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


# UPLOAD AND DOWNLOAD PRESIGNED URL ENDPOINTS
@user_router.put("/upload")
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
@user_router.put("/download")
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
