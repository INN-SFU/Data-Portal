import json
import os
from uuid import uuid5, NAMESPACE_DNS, UUID

from fastapi import Depends, HTTPException, APIRouter, status, Query, Body
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi_mail import MessageSchema, FastMail

from api.v0_1.endpoints.dependencies import get_user_manager
from api.v0_1.endpoints.dependencies import get_policy_manager
from api.v0_1.endpoints.dependencies import get_endpoint_manager

from core.connectivity.agent_factory import new_endpoint
from core.connectivity.agents.models import EndpointConfig
from core.management.endpoints import AbstractEndpointManager
from core.management.policies import AbstractPolicyManager
from core.management.users import AbstractUserManager

from api.v0_1.emailer import conf as email_config
from api.v0_1.endpoints.service.auth import decode_token, is_user_admin

admin_router = APIRouter(prefix='/admin')
templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))


@admin_router.get("/test", dependencies=[Depends(decode_token)])
async def admin_route(user: dict = Depends(decode_token)) -> JSONResponse:
    """
    A test route that can only be accessed by administrators.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Welcome, administrator!"})


@admin_router.put("/register_user", response_class=JSONResponse, dependencies=[Depends(decode_token)])
async def register_user(username: str = Query(...),
                        role: str = Query(...),
                        user: dict = Depends(decode_token)
                        ) -> JSONResponse:
    """
    Registers a user and sends their User ID and Access Key to the provided email.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # User registration
    try:
        response = await add_user_(username, role)
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
        recipients=[username],
        body=f"Your user id/login is:\n\t{username}\nYour access key is {access_key}",
        subtype="plain"
    )
    fm = FastMail(email_config)
    try:
        await fm.send_message(message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f'Sign up failed: {str(e)}')
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={'detail': f"Sign up successful. User ID and Access Key sent to {username}"})


@admin_router.get("/user", dependencies=[Depends(decode_token)])
async def get_user_(username: str = Query(...),
                    user: dict = Depends(decode_token),
                    user_manager: AbstractUserManager = Depends(get_user_manager)) -> JSONResponse:
    """
    Retrieve a user's information.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Retrieve the users uuid
    uuid = user_manager.get_user_uid(username)

    # Retrieve the user info
    user_info = user_manager.get_user(uuid)

    if not user_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return JSONResponse(status_code=status.HTTP_200_OK, content={'user': user_info})


@admin_router.put("/user/", response_class=JSONResponse)
async def add_user_(username: str = Query(...),
                    role: str = Query(...),
                    user: dict = Depends(decode_token),
                    user_manager: AbstractUserManager = Depends(get_user_manager),
                    policy_manager: AbstractPolicyManager = Depends(get_policy_manager)
                    ) -> JSONResponse:
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Create user in Keycloak
    try:
        user_details = {
            "username": username,
            "email": username,
            "enabled": True,
            "role": role,
            "credentials": [{"value": "default_password", "temporary": False}]
        }

        # Try to create the user
        uuid = user_manager.create_user(user_details)

        # Add a policy file if successfully created
        policy_manager.create_user_policy_store(uuid)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    user_details = user_manager.get_user(uuid)

    return JSONResponse(status_code=status.HTTP_201_CREATED,
                        content={"success": "User added successfully", "details": user_details})


@admin_router.delete("/user/", response_class=JSONResponse)
async def remove_user(username: str = Query(...),
                      user: dict = Depends(decode_token),
                      user_manager: AbstractUserManager = Depends(get_user_manager),
                      policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                      ) -> JSONResponse:
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Remove user
    try:
        uuid = user_manager.get_user_uid(username)
        if not uuid:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user_manager.delete_user(uuid)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to remove user:" + str(e))

    # Remove policy file
    try:
        policy_manager.remove_user_policy_store(uuid)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"success": f"User {username} removed."})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="User removed but failed to remove user policy file:" + str(e))


@admin_router.get("/policy", dependencies=[Depends(decode_token)])
async def get_policies(username: str = Query(None),
                       access_point_name: str = Query(None),
                       resource: str = Query(None), action: str = Query(None),
                       user: dict = Depends(decode_token),
                       user_manager: AbstractUserManager = Depends(get_user_manager),
                       policy_manager: AbstractPolicyManager = Depends(get_policy_manager)
                       ) -> JSONResponse:
    """
    Retrieve a policy.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    uuid = user_manager.get_user_uid(username)
    access_point_uid = user_manager.get_user_uid(access_point_name)
    policy = policy_manager.get_policy(uuid, access_point_uid, resource, action)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found.")

    return JSONResponse(status_code=status.HTTP_200_OK, content={"policy": policy})


@admin_router.put("/policy", dependencies=[Depends(decode_token)])
async def add_policy(username: str = Query(...),
                     access_point: str = Query(...),
                     resource: str = Query(...),
                     action: str = Query(...),
                     user_manager: AbstractUserManager = Depends(get_user_manager),
                     policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                     endpoint_manager: AbstractEndpointManager = Depends(get_endpoint_manager),
                     user: dict = Depends(decode_token)) -> JSONResponse:
    """
    Add a policy.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Get the user uid
    uuid = user_manager.get_user_uid(username)
    # Convert access point name to uid
    access_point_uid = endpoint_manager.get_uid(access_point)

    if uuid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if access_point_uid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access point not found")

    try:
        policy_manager.add_policy(uuid, access_point_uid, resource, action)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"success": f"Policy {(username, access_point, resource, action)} added."})


@admin_router.delete("/policy", dependencies=[Depends(decode_token)])
async def remove_policy(username: str = Query(...),
                        access_point: str = Query(...),
                        resource: str = Query(...),
                        action: str = Query(...),
                        user_manager: AbstractUserManager = Depends(get_user_manager),
                        policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                        endpoint_manager: AbstractEndpointManager = Depends(get_endpoint_manager),
                        user: dict = Depends(decode_token)) -> JSONResponse:
    """
    Remove a policy.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Get the user uid
    uuid = user_manager.get_user_uid(username)
    # Convert access point name to uid
    access_point_uid = endpoint_manager.get_uid(access_point)

    if uuid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if access_point_uid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access point not found")

    # Remove the policy
    try:
        policy_manager.remove_policy(uuid, access_point_uid, resource, action)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"success": f"Policy {(username, access_point, resource, action)} removed."})

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@admin_router.get("/assets/", dependencies=[Depends(decode_token)])
async def list_assets(access_point_name: str = Query(...),
                      pattern: str = Query(None),
                      user_manager: AbstractUserManager = Depends(get_user_manager),
                      user: dict = Depends(decode_token)) -> JSONResponse:
    """
    Returns a list of resources matching the provided regex from the given storage access point.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Get the access point uid
    access_point_uid = user_manager.get_user_uid(access_point_name)
    if access_point_uid not in storage_endpoints.keys():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access point not found")

    try:
        endpoint = storage_endpoints[access_point_uid]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Access point {access_point_name} not found.")

    assets = endpoint.get_file_paths(pattern)
    return JSONResponse(content={"assets": assets})


@admin_router.put("/assets/publish", dependencies=[Depends(decode_token)])
async def publish_asset(
                        access_point_name: str = Query(...),
                        resource: str = Query(...), action: str = Query(...),
                        user_manager: AbstractUserManager = Depends(get_user_manager),
                        policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                        user: dict = Depends(decode_token)) -> JSONResponse:
    """
    Publish an asset to be visible to the public.

    :param policy_manager:
    :param user_manager:
    :param user: The user token payload.
    :param access_point_name: The storage access point.
    :param resource: The resource regular expression.
    :param action: The published action for the resource, e.g. 'read' or 'write'.
    :return: A JSON listing the published assets.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Get the access point uid
    try:
        access_point_uid = user_manager.get_user_uid(access_point_name)
        endpoint = storage_endpoints[access_point_uid]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Access point {access_point_name} not found.")

    # Add the policy
    policy_manager.add_policy("public", access_point_uid, resource, action)
    return JSONResponse(content={"assets": endpoint.get_file_paths(resource)})


@admin_router.get("/endpoints/", dependencies=[Depends(decode_token)])
async def list_endpoints(user: dict = Depends(decode_token)) -> JSONResponse:
    """
    Returns a list of storage endpoints issued by the administrator.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Use the gather_endpoints() helper to retrieve endpoint data
    details = gather_endpoints()
    return JSONResponse(content={"endpoints": details})


# todo: Continue integration here
@admin_router.post("/endpoints/", dependencies=[Depends(decode_token)])
async def create_new_endpoint(config: EndpointConfig = Body(...),
                              token_payload: dict = Depends(decode_token)) -> JSONResponse:
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
            pm.add_policy(token_payload.get("preferred_username"), endpoint_uid, ".*", ".*")
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


@admin_router.delete("/endpoints/", dependencies=[Depends(decode_token)])
async def remove_endpoint(endpoint_uid: str = Query(...),
                          user: dict = Depends(decode_token)) -> JSONResponse:
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
