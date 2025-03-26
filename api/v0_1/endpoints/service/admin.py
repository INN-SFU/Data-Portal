import json
import os
from uuid import uuid5, NAMESPACE_DNS

from fastapi import Depends, HTTPException, APIRouter, status, Query, Body, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi_mail import MessageSchema, FastMail

from core.authentication.keycloak_utils import keycloak_administrator
from core.data_access_manager import dam
from core.connectivity import new_endpoint
from core.connectivity.agents.models import EndpointConfig
from core.settings.endpoints import storage_endpoints

from api.v0_1.emailer import conf as email_config
from api.v0_1.endpoints.service.auth import get_current_user, is_user_admin

admin_router = APIRouter(prefix='/admin')
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


def gather_endpoints():
    """
    Returns a dictionary of all storage endpoints:
    {endpoint_uid: endpoint_config, ...}
    """
    return dict(
        zip(
            storage_endpoints.keys(),
            [endpoint.get_config() for endpoint in storage_endpoints.values()]
        )
    )


@admin_router.get("/test", dependencies=[Depends(get_current_user)])
async def admin_route(user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    A test route that can only be accessed by administrators.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Welcome, administrator!"})


@admin_router.put("/register_user", response_class=JSONResponse, dependencies=[Depends(get_current_user)])
async def register_user(uid: str = Query(...), role: str = Query(...),
                        user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    Registers a user and sends their User ID and Access Key to the provided email.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # User registration
    try:
        response = await add_user_(uid, role)
        response_json = json.loads(response.body)
        access_key = response_json.get('access_key')
        if not access_key:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Access key not found in response")
    except KeyError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Access key not found in response")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Send confirmation email
    message = MessageSchema(
        subject="Welcome to the INN Data Portal",
        recipients=[uid],
        body=f"Your user id/login is:\n\t{uid}\nYour access key is {access_key}",
        subtype="plain"
    )
    fm = FastMail(email_config)
    try:
        await fm.send_message(message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f'Sign up failed: {str(e)}')
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={'detail': f"Sign up successful. User ID and Access Key sent to {uid}"})


@admin_router.get("/user", dependencies=[Depends(get_current_user)])
async def get_user_(uid: str = Query(...), user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    Retrieve a user or list all users.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    if uid == "list":
        return JSONResponse(status_code=status.HTTP_200_OK, content=dam.get_users(uid))
    user_info = dam.get_user(uid)
    if not user_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return JSONResponse(status_code=status.HTTP_200_OK, content={'user': user_info})


@admin_router.put("/user/", response_class=JSONResponse)
async def add_user_(uid: str = Query(...), role: str = Query(...),
                    user: dict = Depends(get_current_user)) -> JSONResponse:
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Create user in Keycloak
    try:
        keycloak_user_id = keycloak_administrator.create_user({
            "username": uid,
            "email": uid,
            "enabled": True,
            "credentials": [{"value": "default_password", "temporary": False}],
        })
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Update DAM
    user_uuid = uuid5(NAMESPACE_DNS, uid)
    try:
        user_access_key = dam.add_user(uid, user_uuid, role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists.")

    return JSONResponse(status_code=status.HTTP_201_CREATED,
                        content={"success": "User added successfully", "uid": uid, "access_key": user_access_key})


@admin_router.delete("/user/", response_class=JSONResponse)
async def remove_user(uid: str = Query(...), user: dict = Depends(get_current_user)) -> JSONResponse:
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Remove user from Keycloak
    try:
        users = keycloak_administrator.get_users(query={"username": uid})
        if not users:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        keycloak_user_id = users[0]["id"]
        keycloak_administrator.delete_user(keycloak_user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Remove from DAM
    try:
        result = dam.remove_user(uid)
        if result:
            return JSONResponse(status_code=status.HTTP_200_OK, content={"success": f"User {uid} removed."})
        else:
            raise ValueError("Failed to remove user.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.get("/policy", dependencies=[Depends(get_current_user)])
async def get_policies(uid: str = Query(None), access_point: str = Query(None),
                       resource: str = Query(None), action: str = Query(None),
                       user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    Retrieve a policy.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    policy = dam.enforcer.get_policy(uid, access_point, resource, action)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found.")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"policy": policy})


@admin_router.put("/policy", dependencies=[Depends(get_current_user)])
async def add_policy(uid: str = Query(...), access_point: str = Query(...),
                     resource: str = Query(...), action: str = Query(...),
                     user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    Add a policy.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    if uid not in dam.get_users():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if access_point not in storage_endpoints.keys():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access point not found")

    try:
        dam.add_user_policy(uid, access_point, resource, action)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"success": f"Policy {(uid, access_point, resource, action)} added."})


@admin_router.delete("/policy", dependencies=[Depends(get_current_user)])
async def remove_policy(uid: str = Query(...), access_point: str = Query(...),
                        resource: str = Query(...), action: str = Query(...),
                        user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    Remove a policy.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    try:
        result = dam.remove_policy(uid, access_point, resource, action)
        if result:
            return JSONResponse(status_code=status.HTTP_200_OK,
                                content={"success": f"Policy {(uid, access_point, resource, action)} removed."})
        else:
            raise ValueError("Failed to remove policy.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.get("/assets/", dependencies=[Depends(get_current_user)])
async def list_assets(access_point: str = Query(...), pattern: str = Query(None),
                      user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    Returns a list of resources matching the provided regex from the given storage access point.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    try:
        endpoint = storage_endpoints[access_point]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Access point {access_point} not found.")
    assets = endpoint.get_file_paths(pattern)
    return JSONResponse(content={"assets": assets})


@admin_router.get("/endpoints/", dependencies=[Depends(get_current_user)])
async def list_endpoints(user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    Returns a list of storage endpoints issued by the administrator.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Use the gather_endpoints() helper to retrieve endpoint data
    details = gather_endpoints()
    return JSONResponse(content={"endpoints": details})


@admin_router.post("/endpoints/", dependencies=[Depends(get_current_user)])
async def create_new_endpoint(config: EndpointConfig = Body(...),
                              token_payload: dict = Depends(get_current_user)) -> JSONResponse:
    """
    Add a new storage endpoint.

    Accepts a JSON payload with a "flavour" field and additional fields depending on the selected flavour.
    """
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    try:
        # Extract flavour and convert the Pydantic model to a dict (excluding the flavour field)
        flavour = config.flavour
        config_dict = config.dict(exclude={"flavour"})

        # Generate a new uid for the endpoint using the access_point_slug.
        endpoint_uid = str(uuid5(NAMESPACE_DNS, config_dict['access_point_slug']))

        # Create the endpoint using your factory function.
        endpoint = new_endpoint(flavour, config_dict)

        # Build the configuration file path and get the endpoint configuration.
        endpoint_config_json = os.path.join(os.getenv('ENDPOINT_CONFIGS'), f"{endpoint_uid}.json")
        endpoint_config = {
            "flavour": flavour,
            "config": endpoint._get_config()
        }

        # Optionally: add an admin policy for read
        try:
            dam.add_user_policy(token_payload.get("preferred_username"), endpoint_uid, ".*", "read")
        except ValueError:
            pass

        with open(endpoint_config_json, 'w') as f:
            json.dump(endpoint_config, f, indent=4)

        # Add the endpoint to the global registry.
        storage_endpoints[endpoint_uid] = endpoint

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": f"Endpoint '{endpoint.access_point_slug}' created successfully."}
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.delete("/endpoints/", dependencies=[Depends(get_current_user)])
async def remove_endpoint(endpoint_uid: str = Query(...),
                          user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    Remove a storage endpoint.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    try:
        endpoint = storage_endpoints[endpoint_uid]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Access point {endpoint_uid} not found.")

    endpoint_config_json = os.path.join(os.getenv('ENDPOINT_CONFIGS'), f"{endpoint_uid}.json")
    os.remove(endpoint_config_json)
    del storage_endpoints[endpoint_uid]

    return JSONResponse(content={"detail": f"Endpoint '{endpoint_uid}' removed."})
