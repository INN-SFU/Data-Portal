import logging

from fastapi import HTTPException, APIRouter, Depends, status, Query
from fastapi.security import HTTPBasic
from api.v0_1.endpoints.utils.server import validate_credentials

from core.connectivity import agents
from core.data_access_manager import dam

security = HTTPBasic()
user_router = APIRouter(prefix='/user')

logger = logging.getLogger("uvicorn")


@user_router.get("/assets", dependencies=[Depends(validate_credentials)])
def list_assets(uid: str = Depends(validate_credentials)):
    """
    Retrieves assets for a user.

    Parameters:
    - **uid** (str): The User ID of the validated user.

    Returns:
    - **dict**: The assets for the user.

    Raises:
    - **HTTPException**: If the provided credentials are invalid.
    """
    # Retrieve assets for user_id
    assets = dam.get_all_user_assets(uid)

    # Valid Response
    return {"assets": assets}


@user_router.put("/upload", dependencies=[Depends(validate_credentials)])
def put_asset(uid: str = Depends(validate_credentials), resource: str = Query(...), access_point: str = Query(...)) -> dict:
    """
    Sends a PUT request to the asset router to generate a presigned URL for uploading a file.

    Parameters:
    - **uid** (str): The User ID from the validated user.
    - **resource** (str): The name of resource location to upload to.
    - **access_point** (str): The name of the storage access point where the resource is located.

    Returns:
    - **dict**: The presigned URL for uploading the file.

    Raises:
    - **HTTPException**: If the asset router URL is not found or the file cannot be uploaded (status code 404).
    - **HTTPException**: If the user does not have write access to the resource (status code 403).
    """
    if dam.validate_user_access(uid, access_point, resource, "write"):
        try:
            agent = agents[access_point]
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Access point {access_point} not found.")

        presigned_urls, file_paths = agent.generate_access_links(f"{resource}", 'PUT', 3600)
        return {"presigned_urls": presigned_urls, 'file_paths': file_paths}

    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="User does not have write access to this resource")


@user_router.put("/download", dependencies=[Depends(validate_credentials)])
def get_asset(uid: str = Depends(validate_credentials), resource: str = Query(...), access_point: str = Query(...)) -> dict:
    """
    Get presigned URLs for downloading the specified asset.

    Parameters:
    - **uid** (str): The User ID from the validated user.
    - **resource** (str): The name of resource location to upload to.
    - **access_point** (str): The name of the storage access point where the resource is located.

    Returns:
    - **dict**: The presigned URLs for the asset.

    Raises:
    - **HTTPException**: If the asset is not found (status code 404).
    - **HTTPException**: If the user does not have access to the asset (status code 403).
    """

    if dam.validate_user_access(uid, access_point, resource, "read"):

        try:
            agent = agents[access_point]
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Access point {access_point} not found.")

        presigned_urls, file_paths = agent.generate_access_links(resource, 'GET', 600)
        return {"presigned_urls": presigned_urls, 'file_paths': file_paths}

    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="User does not have access to the specified resource")
