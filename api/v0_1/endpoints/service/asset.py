import logging
from fastapi import HTTPException, APIRouter, Depends, status, Query
from fastapi.responses import JSONResponse

from api.v0_1.endpoints.dependencies import get_policy_manager
from api.v0_1.endpoints.dependencies.managers import get_endpoint_manager
from api.v0_1.endpoints.service.auth import decode_token
from core.connectivity import agents
from core.management.endpoints.abstract_endpoint_manager import AbstractEndpointManager
from core.management.policies import AbstractPolicyManager

asset_router = APIRouter(prefix='/asset')
logger = logging.getLogger("uvicorn")


@asset_router.get("/assets", dependencies=[Depends(decode_token)])
def list_assets(uid_payload: dict = Depends(decode_token),
                access_point: str = Query(None),
                endpoint_manager: AbstractEndpointManager = Depends(get_endpoint_manager),
                policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
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

    if access_point is not None:
        if not endpoint_manager.get_uid(access_point):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Access point {access_point} not found.")
    if action is not None:
        action = action.lower()

    # Retrieve policies according to the filters
    policies = policy_manager.filter_policies(uid, access_point, action)

    # Retrieve file names based on filtered policies.
    assets = {agent: [] for agent in set(policies.keys())}
    for agent in policies.keys():
        for asset_reg_ex in policies[agent]:
            assets[agent].append(agents[agent].get_file_paths(asset_reg_ex))
    return JSONResponse(status_code=status.HTTP_200_OK, content={"assets": assets})


@asset_router.put("/upload", dependencies=[Depends(decode_token)])
def put_asset(uid_payload: dict = Depends(decode_token), resource: str = Query(...),
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
    if pm.validate_policy(uid, access_point, resource, "write"):
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


@asset_router.put("/download", dependencies=[Depends(decode_token)])
def get_asset(uid_payload: dict = Depends(decode_token), resource: str = Query(...),
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
    if pm.validate_policy(uid, access_point, resource, "read"):
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

