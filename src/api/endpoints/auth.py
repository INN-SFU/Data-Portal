from typing import Annotated

import jwt
from fastapi import Request, Depends, HTTPException, APIRouter
from fastapi.security import HTTPBasicCredentials, HTTPBasic

from src.api.internal.authentication.auth import validate_credentials, generate_token, token_expired

security = HTTPBasic()
router = APIRouter(prefix='/auth')


@router.get("")
def auth(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    """
    Handler for the auth endpoint.
    :param credentials:   The HTTP Basic credentials.
    :return:
    """
    uid = credentials.username
    password = credentials.password
    if validate_credentials(uid, password):
        return {"success": "Valid credentials"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/token")
def get_token(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    """
    Handler for the get token endpoint.
    :param credentials:
    :return:
    """

    uid = credentials.username
    password = credentials.password
    if validate_credentials(uid, password):
        token = generate_token(uid, password, 300)
        return {"token": token}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/token/{token}")
def validate_token_(request: Request, token: str):
    """
    Handler for the validate token endpoint.

    :param token: The token to be validated.
    :param request: The incoming request object.
    :type request: Request
    :return: The rendered validate_token.html template.
    :rtype: templates.TemplateResponse
    """
    if not token:
        raise HTTPException(status_code=400, detail="No token provided")

    try:
        valid = token_expired(token)
    except jwt.exceptions.DecodeError:
        valid = False

    if valid:
        return {"success": "Valid token"}
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
