from typing import Annotated

import jwt

from fastapi import Depends, HTTPException, APIRouter, status, Query
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from fastapi.responses import JSONResponse

from core.data_access_manager import dam
from core.authentication import validate_credentials, generate_token, token_expired

from api.v0_1.emailer import conf as email_conf

security = HTTPBasic()
auth_router = APIRouter(prefix='/auth')


@auth_router.get("/test", response_class=JSONResponse)
def auth(credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> JSONResponse:
    """
    Authenticate the user using the provided credentials.

    Parameters:
    - **credentials** (HTTPBasicCredentials): The HTTP basic authentication credentials, including:
        - **username**: The user's User ID
        - **password**: The user's Key.

    Returns:
    - **JSONResponse**: A message indicating whether the credentials are valid or not.

    Raises:
    - **HTTPException**: If the credentials are invalid.
    """
    uid = credentials.username
    password = credentials.password
    if validate_credentials(uid, password):
        return JSONResponse(status_code=status.HTTP_200_OK, content={"success": "Valid credentials"})
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@auth_router.post("/login", response_class=JSONResponse)
def login(credentials: HTTPBasicCredentials = Depends(security)) -> JSONResponse:
    """
    Authenticate a user and retrieve their role based on the provided credentials.

    Parameters:
    - **credentials** (HTTPBasicCredentials): An instance of the `HTTPBasicCredentials` class containing:
        - **username**: The user's User ID (UID).
        - **password**: The user's Key.

    Returns:
    - **JSONResponse**: If the credentials are valid, returns a JSON object containing:
        - **uid**: The user's UID.
        - **role**: The user's role (admin or user).

    Raises:
    - **HTTPException**: If the credentials are invalid, raises an HTTPException with a status code of 401 and a detail message indicating the invalid credentials.
    """
    uid = credentials.username
    key = credentials.password

    if uid not in dam.get_all_users():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    elif not validate_credentials(uid, key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    else:
        role = dam.get_user(uid)['role']
        return JSONResponse(status_code=status.HTTP_200_OK, content={'uid': uid, 'role': role})


@auth_router.get("/token", response_class=JSONResponse)
def get_token(credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> JSONResponse:
    """
    Handler for the get token endpoint.

    Parameters:
    - **credentials** (HTTPBasicCredentials): The HTTP basic authentication credentials, including:
        - **username**: The user's UID.
        - **password**: The user's Key.

    Returns:
    - **JSONResponse**: A JSON response containing:
        - **token**: the generated token.

    Raises:
    - **HTTPException**: If the credentials are invalid.
    """
    uid = credentials.username
    password = credentials.password
    if validate_credentials(uid, password):
        token = generate_token(uid, password, 300)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"token": token})
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@auth_router.post("/token")
def validate_token_(token: str = Query(...)) -> JSONResponse:
    """
    Handler for the validate token endpoint.

    Parameters:
    - **token** (str): The token to be validated.

    Returns:
    - **JSONResponse**: A JSON response containing indicating if the token is valid or not.

    Raises:
    - **HTTPException**: If the token is invalid.
    """
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No token provided")

    try:
        valid = token_expired(token)
    except jwt.exceptions.DecodeError:
        valid = False

    if valid:
        return JSONResponse(status_code=status.HTTP_200_OK, content={"detail": "Valid token"})
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
