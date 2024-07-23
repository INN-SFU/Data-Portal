import logging

from fastapi import Request, HTTPException, APIRouter, Depends, status
from fastapi.security import HTTPBasic
from api.v0_1.endpoints.utils.server import validate_credentials

from core.connectivity import agents
from core.data_access_manager import dam

security = HTTPBasic()
user_router = APIRouter(prefix='/user')

logger = logging.getLogger("uvicorn")


@user_router.get("/list")
def read_assets(creds: str = Depends(validate_credentials)):
    """
    Retrieves assets for a user.

    Parameters:
    - **creds** (str): The credentials required for authentication.

    Returns:
    - **dict**: The assets for the user.

    Raises:
    - **HTTPException**: If the provided credentials are invalid.
    """
    uid = creds[0]

    # Retrieve assets for user_id
    assets = dam.get_all_user_assets(uid)

    # Valid Response
    return {"assets": assets}


@user_router.put("/upload")
def put_asset(request: Request, creds: str = Depends(validate_credentials)) -> dict:
    """
    Sends a PUT request to the asset router to generate a presigned URL for uploading a file.

    Parameters:
    - **request** (Request): The request object.
    - **creds** (str): The credentials required for authentication.

    Returns:
    - **dict**: The presigned URL for uploading the file.

    Raises:
    - **HTTPException**: If the asset router URL is not found or the file cannot be uploaded (status code 404).
    - **HTTPException**: If the user does not have write access to the resource (status code 403).
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
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="User does not have write access to this resource")


@user_router.put("/download")
def get_asset(request: Request, creds: str = Depends(validate_credentials)) -> dict:
    """
    Get presigned URLs for downloading the specified asset.

    Parameters:
    - **request** (Request): The request object.
    - **creds** (str): The user credentials.

    Returns:
    - **dict**: The presigned URLs for the asset.

    Raises:
    - **HTTPException**: If the asset is not found (status code 404).
    - **HTTPException**: If the user does not have access to the asset (status code 403).
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
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="User does not have access to the specified resource")
