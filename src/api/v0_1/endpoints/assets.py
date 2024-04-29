import os
from fastapi import Request, HTTPException, APIRouter, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.core.authentication import auth
from src.core.settings.config import dam

security = HTTPBasic()
asset_router = APIRouter(prefix='/assets')


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

        url = f"http://{os.getenv('DCS_HOST')}:{os.getenv('DCS_PORT')}/stream?token={token}"
        return templates.TemplateResponse("dcs_link.html", {"request": request, "url": url})

    else:
        raise HTTPException(status_code=403, detail="User does not have read access to this resource")


@asset_router.put("")
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
        pass
    else:
        raise HTTPException(status_code=403, detail="User does not have write access to this resource")
