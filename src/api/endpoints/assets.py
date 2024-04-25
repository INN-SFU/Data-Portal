from typing import Annotated

import jwt
from fastapi import Request, HTTPException, APIRouter, UploadFile, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.api.internal.authentication import auth
from src.api.config import dam, arbutus_client

security = HTTPBasic()
router = APIRouter(prefix='/assets')


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
@router.get("/list")
def read_assets(uid: str = Depends(validate_credentials)):
    """
    Retrieves assets for a user.

    :return: The assets for the user.
    :raises HTTPException: If the provided credentials are invalid.
    :rtype: dict
    """
    # Retrieve assets for user_id
    assets = dam.get_policy(uid, '', '', '')

    # Valid Response
    return {"assets": assets}


@router.get("")
def retrieve_asset(request: Request, creds: str = Depends(validate_credentials)):
    """
    This method is used to generate a presigned URL for uploading assets to a resource.

    :param request: The request object containing relevant query parameters.
    :param creds: The user ID and key used to validate user credentials.
    :return: A dictionary containing the presigned URL for uploading the asset.
    :raises HTTPException: If the user does not have write access to the resource.
    """
    uid = creds[0]
    key = creds[1]

    resource = request.query_params.get("resource")
    access_point = request.query_params.get("access_point")

    if dam.validate_user_access(uid, access_point, resource, "read"):
        token = auth.generate_token(uid_slug=uid, key=key, time_to_live=300, access_point=access_point,
                                    resource=resource, action="get-object")

        return {"access_token": token}

    else:
        raise HTTPException(status_code=403, detail="User does not have read access to this resource")


@router.put("")
def put_asset(request: Request, uid: str = Depends(validate_credentials)):
    """
    This method is used to generate a presigned URL for uploading assets to a resource.

    :param request: The request object containing relevant query parameters.
    :param uid: The user ID used to validate user credentials.
    :return: A dictionary containing the presigned URL for uploading the asset.
    :raises HTTPException: If the user does not have write access to the resource.
    """
    resource = request.query_params.get("resource")
    asset_name = request.query_params.get("asset_name")
    asset = request.query_params.get("asset")

    if dam.validate_user_access(uid, resource, "write"):
        presigned_url = arbutus_client.generate_presigned_url(uid, asset_name, asset, action="put-object")
        return {"presigned_url": presigned_url}
    else:
        raise HTTPException(status_code=403, detail="User does not have write access to this resource")
