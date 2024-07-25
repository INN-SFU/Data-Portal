import os
from uuid import uuid5, NAMESPACE_DNS

from fastapi import Depends, HTTPException, APIRouter, status, Query
from fastapi.security import HTTPBasic
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse

from core.connectivity import agents
from core.data_access_manager import dam
from api.v0_1.endpoints.utils.server import is_admin

security = HTTPBasic()
admin_router = APIRouter(prefix='/admin')
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


@admin_router.get("/test", dependencies=[Depends(is_admin)])
async def admin_route():
    """
    A test route that can only be accessed by administrators.

    Returns:
        - **JSONResponse**: A welcome message for the administrator.
    """
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Welcome, administrator!"})


@admin_router.get("/user/{uid}", dependencies=[Depends(is_admin)])
async def get_user_(uid: str):
    """
    Handler for the get user endpoint.

    Parameters:
    - **uid** (str): The user ID or "list" to retrieve all users.

    Returns:
    - **JSONResponse**: The user information if found, or a list of users if "list" is passed as uid.

    Raises:
    - **HTTPException**: If the user is not found.
    """
    if uid == "list":
        return JSONResponse(status_code=status.HTTP_200_OK, content=dam.get_users(uid))

    user = dam.get_user(uid)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return user


@admin_router.put("/user/", dependencies=[Depends(is_admin)])
async def add_user_(uid: str = Query(...), role: str = Query(...)):
    """
    Add a user.

    Parameters:
    - **uid** (str): The unique ID of the user to be added (email).
    - **role** (str): The role of the user ("user" or "admin").

    Returns:
    - **JSONResponse**: A dictionary with the success message and the user's secret key.

    Raises:
    - **HTTPException**: If there is an error adding the user.
    """
    uuid = uuid5(NAMESPACE_DNS, uid)

    if role not in ["admin", "user"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid role. Must be "admin" or "user".')

    try:
        user_secret_key = dam.add_user(uid, uuid, role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists.")

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"success": "User added successfully", "uid": uid, "secret_key": user_secret_key})


@admin_router.delete("/user/", dependencies=[Depends(is_admin)])
async def remove_user(uid: str = Query(...)):
    """
    Delete a user and all their associated data.

    Parameters:
    - **uid** (str): The unique ID of the user to be removed.

    Returns:
    - **JSONResponse**: A dictionary with the success message if the user is removed successfully.

    Raises:
    - **HTTPException**: If there is an error removing the user.
    """
    try:
        result = dam.remove_user(uid)
        if result:
            return JSONResponse(status_code=status.HTTP_200_OK,
                                content={"success": f"User {uid} removed."})
        else:
            raise ValueError("Failed to remove user.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.get("/policy", dependencies=[Depends(is_admin)])
async def get_policies(uid: str = Query(None), access_point: str = Query(None), resource: str = Query(None),
                       action: str = Query(None)):
    """
    Retrieve a policy.

    Parameters:
    - **uid** (str, optional): The user ID.
    - **access_point** (str, optional): The access point.
    - **resource** (str, optional): The resource.
    - **action** (str, optional): The action.

    Returns:
    - **JSONResponse**: A dictionary with the policy information if found.

    Raises:
    - **HTTPException**: If the policy is not found.
    """
    policy = dam.enforcer.get_policy(uid, access_point, resource, action)

    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found.")

    return JSONResponse(status_code=status.HTTP_200_OK, content={"policy": policy})


@admin_router.put("/policy", dependencies=[Depends(is_admin)])
async def add_policy(uid: str = Query(...), access_point: str = Query(...), resource: str = Query(...),
                     action: str = Query(...)):
    """
    Add a policy.

    Parameters:
    - **uid** (str): The user ID.
    - **access_point** (str): The access point.
    - **resource** (str): The resource.
    - **action** (str): The action.

    Returns:
    - **JSONResponse**: A dictionary with the success message if the policy is added successfully.

    Raises:
    - **HTTPException**: If there is an error adding the policy.
    """
    # Check if the user exists
    if uid not in dam.get_users():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Check if the access point exists
    if access_point not in [agent.access_point_slug for agent in agents]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access point not found")

    try:
        dam.add_user_policy(uid, access_point, resource, action)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"success": f"Policy {(uid, access_point, resource, action)} added."})


@admin_router.delete("/policy", dependencies=[Depends(is_admin)])
async def remove_policy(uid: str = Query(...), access_point: str = Query(...), resource: str = Query(...),
                        action: str = Query(...)):
    """
    Remove a policy.

    Parameters:
    - **uid** (str): The user ID.
    - **access_point** (str): The access point.
    - **resource** (str): The resource.
    - **action** (str): The action.

    Returns:
    - **JSONResponse**: A dictionary with the success message if the policy is removed successfully.

    Raises:
    - **HTTPException**: If there is an error removing the policy.
    """
    try:
        result = dam.remove_policy(uid, access_point, resource, action)
        if result:
            return JSONResponse(status_code=status.HTTP_200_OK,
                                content={"success": f"Policy {(uid, access_point, resource, action)} removed."})
        else:
            raise ValueError("Failed to remove policy.")

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.get("/assets/", dependencies=[Depends(is_admin)])
async def list_assets(access_point: str = Query(...), pattern: str = Query(None)):
    """
    Returns a list of resources matching the provided regular expression from the given storage access point.

    Parameters:
    - **access_point** (str): The access point to list resources from.
    - **pattern** (str, optional): The regular expression to filter out resources. If not provide all resources are
        returned.

    Returns:
    - **JSONResponse**: A JSON response with a list of matching assets.

    Raises:
    - **HTTPException**: If the credentials are invalid.
    """
    try:
        agent = agents[access_point]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Access point {access_point} not found.")
    assets = agent.get_file_paths(pattern)
    return JSONResponse(content={"assets": assets})
