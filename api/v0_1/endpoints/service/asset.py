import logging
from fastapi import HTTPException, APIRouter, Depends, status, Query
from fastapi.responses import JSONResponse

from api.v0_1.endpoints.service.auth import get_current_user
from core.connectivity import agents
from core.data_access_manager import dam

asset_router = APIRouter(prefix='/asset')
logger = logging.getLogger("uvicorn")


@asset_router.get("/assets", dependencies=[Depends(get_current_user)])
def list_assets(uid_payload: dict = Depends(get_current_user), access_point: str = Query(None),
                action: str = Query(None)) -> JSONResponse:
    """
    Retrieves information about available assets for a user.

    Parameters:
    - uid_payload (dict): Token claims extracted from Keycloak.
    - access_point (str): The storage access point to filter assets by. If None, all are searched.
    - action (str): The action type ("read" or "write") to filter assets by.

    Returns:
    - JSONResponse: A JSON containing a list of asset keys the user has access to.
    """
    uid = uid_payload.get("preferred_username")
    # Retrieve policies according to the filters
    policies = dam.get_all_user_policies(uid, access_point, action)

    # Retrieve file names based on filtered policies.
    assets = {agent: [] for agent in set(policies.keys())}
    for agent in policies.keys():
        for asset_reg_ex in policies[agent]:
            assets[agent].append(agents[agent].get_file_paths(asset_reg_ex))
    return JSONResponse(status_code=status.HTTP_200_OK, content={"assets": assets})


@asset_router.put("/upload", dependencies=[Depends(get_current_user)])
def put_asset(uid_payload: dict = Depends(get_current_user), resource: str = Query(...),
              access_point: str = Query(...)) -> JSONResponse:
    """
    Generate presigned URL(s) for uploading a file.

    Parameters:
    - uid_payload (dict): The token claims from Keycloak.
    - resource (str): The resource path for the upload.
    - access_point (str): The storage access point.

    Returns:
    - JSONResponse: A JSON containing presigned URLs and file paths.
    """
    uid = uid_payload.get("preferred_username")
    if dam.validate_user_access(uid, access_point, resource, "write"):
        try:
            agent = agents[access_point]
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Access point {access_point} not found.")
        presigned_urls, file_paths = agent.generate_access_links(str(resource), 'PUT', 3600)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"presigned_urls": presigned_urls, "file_paths": file_paths})
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="User does not have write access to this resource")


@asset_router.put("/download", dependencies=[Depends(get_current_user)])
def get_asset(uid_payload: dict = Depends(get_current_user), resource: str = Query(...),
              access_point: str = Query(...)) -> JSONResponse:
    """
    Generate presigned URL(s) for downloading a file.

    Parameters:
    - uid_payload (dict): The token claims from Keycloak.
    - resource (str): The resource path for the download.
    - access_point (str): The storage access point.

    Returns:
    - JSONResponse: A JSON containing presigned URLs and file paths.
    """
    uid = uid_payload.get("preferred_username")
    if dam.validate_user_access(uid, access_point, resource, "read"):
        try:
            agent = agents[access_point]
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Access point {access_point} not found.")
        presigned_urls, file_paths = agent.generate_access_links(resource, 'GET', 600)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"presigned_urls": presigned_urls, "file_paths": file_paths})
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="User does not have access to the specified resource")
