import logging

from fastapi import HTTPException, APIRouter, Depends, status, Query
from fastapi.responses import JSONResponse

from api.v0_1.endpoints.dependencies import get_policy_manager
from api.v0_1.endpoints.dependencies.managers import get_endpoint_manager, get_user_manager
from api.v0_1.endpoints.service.auth import decode_token
from api.v0_1.endpoints.service.models import GetAssetRequest, GetAssetResponse, PutAssetRequest, PutAssetResponse
from core.management.endpoints import AbstractEndpointManager
from core.management.policies import AbstractPolicyManager, Policy
from core.management.users import AbstractUserManager

asset_router = APIRouter(prefix='/asset', tags=["Assets"])
logger = logging.getLogger("uvicorn")


@asset_router.put("/upload", dependencies=[Depends(decode_token)])
def put_asset(asset: PutAssetRequest = Depends(),
              user: dict = Depends(decode_token),
              user_manager: AbstractUserManager = Depends(get_user_manager),
              policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
              endpoint_manager: AbstractEndpointManager = Depends(get_endpoint_manager)
              ) -> PutAssetResponse:

    # Unpack the request
    user_uuid = user_manager.get_user_uuid(user['preferred_username'])
    access_point = asset.access_point
    access_point_uuid = endpoint_manager.get_endpoint_uuid(access_point)
    resource = asset.resource

    policy = Policy(
        user_uuid=user_uuid,
        endpoint_uuid=access_point_uuid,
        resource=resource,
        action='write'
    )

    if policy_manager.validate_policy(policy):
        try:
            agent = endpoint_manager.get_endpoint_by_uuid(access_point_uuid).agent
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Access point {access_point} not found.")

        presigned_urls, file_paths = agent.generate_access_link(str(resource), 'write', 3600)
        return PutAssetResponse(
            presigned_urls=presigned_urls,
            file_paths=file_paths
        )

    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="User does not have write access to this resource")


@asset_router.put("/download", dependencies=[Depends(decode_token)])
def get_asset(asset: GetAssetRequest = Depends(),
              user: dict = Depends(decode_token),
              user_manager: AbstractUserManager = Depends(get_user_manager),
              policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
              endpoint_manager: AbstractEndpointManager = Depends(get_endpoint_manager)
              ) -> GetAssetResponse:

    # Get the user uuid
    user_uuid = user_manager.get_user_uuid(user['preferred_username'])

    #
    try:
        access_point_uuid = endpoint_manager.get_endpoint_uuid(asset.access_point)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Access point {asset.access_point} not found.")

    # Build the policy
    policy = Policy(
        user_uuid=user_uuid,
        endpoint_uuid=access_point_uuid,
        resource=asset.resource,
        action=asset.action
    )

    if policy_manager.validate_policy(policy):
        agent = endpoint_manager.get_endpoint_by_uuid(access_point_uuid).agent
        try:
            presigned_urls, file_paths = agent.generate_access_link(policy.resource, policy.action, 600)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Unable to generate presigned URL: {str(e)}")
        return GetAssetResponse(
            presigned_urls=presigned_urls,
            file_paths=file_paths
        )
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="User does not have access to the specified resource")

