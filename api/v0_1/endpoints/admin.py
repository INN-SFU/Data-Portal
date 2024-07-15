import os

from uuid import uuid5, NAMESPACE_DNS
from fastapi import Request, Depends, HTTPException, APIRouter
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from treelib import Tree

from core.authentication.auth import validate_credentials
from core.settings import agents
from core.settings import dam

security = HTTPBasic()
admin_router = APIRouter(prefix='/admin')
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


# UTILITES/HELPER FUNCTIONS
def convert_file_tree_to_dict(tree: Tree):
    tree_data = []
    for node in tree.all_nodes():
        if node.tag != 'root':  # Skip the 'root' node
            parent = tree.parent(node.identifier)
            # If the parent is 'root', treat this node as a top-level node
            parent_id = '#' if parent is None or parent.tag == 'root' else parent.identifier
            tree_data.append(
                {"id": node.identifier, "parent": parent_id, "text": node.tag, "li_attr": {"data-id": node.identifier}}
            )
    return tree_data


# ENDPOINT ACCESS CONTROL
# Define a function to check if the user is an administrator
def is_admin(credentials: HTTPBasicCredentials = Depends(security)):
    uid = credentials.username
    password = credentials.password

    if uid not in dam.get_users():
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if validate_credentials(uid, password) and dam.get_user(uid)['role'] == "admin":
        return uid  # Return uid if user is admin
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


# ADMIN ENDPOINTS
@admin_router.get("", dependencies=[Depends(is_admin)])
async def admin_route():
    return {"message": "Welcome, administrator!"}


# Admin User Endpoints
@admin_router.get("/user/{uid}", dependencies=[Depends(is_admin)])
async def get_user_(uid: str):
    """
    Handler for the get user endpoint.

    :param uid: The user ID.
    :type uid: str
    :return: The rendered user.html template.
    :rtype: templates.TemplateResponse
    """
    if uid == "list":
        return dam.get_users()

    user = dam.get_user(uid)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return dam.get_user(uid)


@admin_router.put("/user/{uid}", dependencies=[Depends(is_admin)])
async def add_user_(request: Request, uid: str):
    """
    Handler for the add user endpoint.

    :param uid: The unique ID of the user to be added.
    :param request: The incoming request object.
    :type request: Request
    :return: The rendered add_user.html template.
    :rtype: templates.TemplateResponse
    """
    role = request.query_params.get("role")
    uuid = uuid5(NAMESPACE_DNS, uid)

    if not role:
        raise HTTPException(status_code=400, detail="No role provided")

    try:
        user_secret_key = dam.add_user(uid, uuid, role)
    except ValueError:
        raise HTTPException(status_code=400, detail="User already exists")

    return {"success": "User added successfully", "uid": uid, "secret_key": user_secret_key}


@admin_router.delete("/user/{uid}", dependencies=[Depends(is_admin)])
async def remove_user(uid: str):
    """
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


# ADMIN POLICY MANAAGEMENT

@admin_router.get("/policy", dependencies=[Depends(is_admin)])
async def get_policies(request: Request):
    """
    Handler for the get policies endpoint.

    :return: The rendered get_policies.html template.
    :rtype: templates.TemplateResponse
    """
    uid = request.query_params.get("uid")
    access_point = request.query_params.get("access_point")
    resource = request.query_params.get("resource")
    action = request.query_params.get("action")
    return dam.get_policy(uid, access_point, resource, action)


@admin_router.put("/policy", dependencies=[Depends(is_admin)])
async def add_policy(request: Request):
    """
    Handler for the add policy endpoint.

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
    Handler for the remove policy endpoint.

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


@admin_router.get("/assets/{access_point}", dependencies=[Depends(is_admin)])
async def get_all_assets(request: Request, access_point: str):
    """
    Handler for the get all assets endpoint.

    :return: The rendered all_assets.html template.
    :rtype: templates.TemplateResponse
    """
    for agent in agents:
        if agent.access_point_slug == access_point:
            return templates.TemplateResponse("file_tree.html",
                                              {"request": request, "tree_json": agent.tree_to_jstree_json()})
    raise HTTPException(status_code=404, detail="Access point not found")


# Policy Management GUIs
@admin_router.get("/file-management", response_class=HTMLResponse, dependencies=[Depends(is_admin)])
async def admin_file_management(request: Request, uid: str = Depends(is_admin)):
    assets = {}
    for agent in agents:
        assets[agent.access_point_slug] = convert_file_tree_to_dict(agent.get_user_file_tree(uid, 'write', dam))
    return templates.TemplateResponse("admin.html", {"request": request, "assets": assets})


# Endpoint to display users and their file access
@admin_router.get("/user-access", response_class=HTMLResponse, dependencies=[Depends(is_admin)])
async def user_access(request: Request):
    users = dam.get_users()
    user_file_trees = {}
    for uid in users:
        user_file_trees[uid] = {}
        for agent in agents:
            user_file_trees[uid][agent.access_point_slug] = convert_file_tree_to_dict(agent.get_user_file_tree(uid, 'read', dam))
    return templates.TemplateResponse("user_access.html", {"request": request, "users": users,
                                                           "user_file_trees": user_file_trees})
