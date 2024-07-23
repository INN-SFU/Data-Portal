from typing import Annotated

import jwt

from fastapi import Request, Depends, HTTPException, APIRouter, status
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from fastapi.responses import JSONResponse

from core.data_access_manager import dam
from core.authentication import validate_credentials, generate_token, token_expired

security = HTTPBasic()
auth_router = APIRouter(prefix='/auth')


@auth_router.get("/test", response_class=JSONResponse)
def auth(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    """
    Authenticate the user using the provided credentials.

    :param credentials: The HTTP basic authentication credentials, an uid (username) and key (password).
    :type credentials: HTTPBasicCredentials
    :return: A JSON response indicating whether the credentials are valid or not.
    :rtype: JSONResponse
    :raises HTTPException: If the credentials are invalid.
    """
    uid = credentials.username
    password = credentials.password
    if validate_credentials(uid, password):
        return JSONResponse(status_code=status.HTTP_200_OK, content={"success": "Valid credentials"})
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


# Handle login submission
@auth_router.post("/login", response_class=JSONResponse)
def login(credentials: HTTPBasicCredentials = Depends(security)):

    uid = credentials.username
    key = credentials.password

    if uid not in dam.get_all_users():
        raise HTTPException(status_code=401, detail="Invalid credentials")
    elif not validate_credentials(uid, key):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    else:
        role = dam.get_user(uid)['role']
        return JSONResponse(status_code=status.HTTP_200_OK, content={'uid': uid, 'role': role})


@auth_router.get("/token", response_class=JSONResponse)
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
        return JSONResponse(status_code=200, content={"token": token})
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@auth_router.post("/token/{token}")
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
