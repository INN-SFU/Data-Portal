import os
from uuid import uuid5, NAMESPACE_DNS

from fastapi import Request, Depends, HTTPException, APIRouter, Form
from fastapi.security import HTTPBasic
from fastapi.templating import Jinja2Templates

from core.connectivity import agents
from core.data_access_manager import dam

from api.v0_1.endpoints.utils.server import is_admin

security = HTTPBasic()
admin_router = APIRouter(prefix='/admin')
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


# Test
@admin_router.get("/test", dependencies=[Depends(is_admin)])
async def admin_route():
    return {"message": "Welcome, administrator!"}


# User View and Control
@admin_router.get("/user/{uid}", dependencies=[Depends(is_admin)])
async def get_user_(uid: str):
    """
    Handler for the get user endpoint.

    :param uid: The user ID.
    :type uid: str
    :return: The rendered home.html template.
    :rtype: templates.TemplateResponse
    """
    if uid == "list":
        return dam.get_users()

    user = dam.get_user(uid)

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    return dam.get_user(uid)


@admin_router.put("/user/", dependencies=[Depends(is_admin)])
async def add_user_(request: Request, uid: str = Form(...), role: str = Form(...)):
    """
    Add a user.

    :param uid: The unique ID of the user to be added (email).
    :param role: Their role (user or admin)
    :param request: The incoming request object.
    :type request: Request
    :return: The rendered add_user.html template.
    :rtype: templates.TemplateResponse
    """
    uuid = uuid5(NAMESPACE_DNS, uid)

    if role != "admin" or "user":
        raise HTTPException(status_code=400, detail="Invalid role. \"admin\" or \"user\".")

    try:
        user_secret_key = dam.add_user(uid, uuid, role)
    except ValueError:
        raise HTTPException(status_code=400, detail="User already exists.")

    return {"success": "User added successfully", "uid": uid, "secret_key": user_secret_key}


@admin_router.delete("/user/{uid}", dependencies=[Depends(is_admin)])
async def remove_user(uid: str):
    """
    Delete a user and all their associated data.

    :param uid: The unique ID of the user to be removed.
    :return: A dictionary with the success message if the user is removed successfully.
    :raises HTTPException: If there is an error removing the user.
    """
    try:
        result = dam.remove_user(uid)
        if result:
            return {"success": "User removed successfully."}
        else:
            raise ValueError("Failed to remove user.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=e.__str__())


# Policy View and Control
@admin_router.get("/policy", dependencies=[Depends(is_admin)])
async def get_policies(request: Request):
    """
    Retrieve a policy.

    :return: The rendered get_policies.html template.
    :rtype: te
    """
    uid = request.query_params.get("uid")
    access_point = request.query_params.get("access_point")
    resource = request.query_params.get("resource")
    action = request.query_params.get("action")
    policy = dam.enforcer.get_policy(uid, access_point, resource, action)

    if policy is None:
        return HTTPException(status_code=404, detail={"failed": "Policy not found."})

    return {"policy": policy}


@admin_router.put("/policy", dependencies=[Depends(is_admin)])
async def add_policy(request: Request):
    """
    Add a policy.

    :param request: The incoming request object.
    :type request: Request
    :return: The rendered add_policy.html template.
    :rtype: templates.TemplateResponse
    """
    uid = request.query_params.get("uid")
    access_point = request.query_params.get("access_point")
    resource = request.query_params.get("resource")
    action = request.query_params.get("action")

    # Check if the user exists
    if uid not in dam.get_users():
        raise HTTPException(status_code=404, detail="User not found")
    # Check if the access point exists
    if access_point not in [agent.access_point_slug for agent in agents]:
        raise HTTPException(status_code=404, detail="Access point not found")

    try:
        dam.add_user_policy(uid, access_point, resource, action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=e.__str__())

    return {"success": "Policy added successfully."}


@admin_router.delete("/policy", dependencies=[Depends(is_admin)])
async def remove_policy(request: Request):
    """
    Remove a policy.

    :param request: The incoming request object.
    :type request: Request
    :return: The rendered remove_policy.html template.
    :rtype: templates.TemplateResponse
    """
    uid = request.query_params.get("uid")
    access_point = request.query_params.get("access_point")
    resource = request.query_params.get("resource")
    action = request.query_params.get("action")

    try:
        result = dam.remove_policy(uid, access_point, resource, action)
        if result:
            return {"success": "Policy removed successfully."}
        else:
            raise ValueError("Failed to remove policy.")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=e.__str__())
