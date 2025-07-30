import os
from uuid import uuid5, NAMESPACE_DNS, UUID

from fastapi import Depends, HTTPException, APIRouter, status, Query, Body
from fastapi.responses import JSONResponse

from core.injection import get_user_manager
from core.injection import get_policy_manager
from core.injection import get_instance_manager
from api.v0_1.endpoints.service.models import (User, AddUserRequest, AddUserResponse, RemoveUserResponse,
                                               GetPolicyResponse, AddPolicyResponse, AddPolicyRequest,
                                               RemovePolicyRequest, RemovePolicyResponse, PolicyManagementData,
                                               UserManagementData, InstanceManagementData, AssetManagementData, 
                                               InstanceCreate, model_registry)
from api.v0_1.endpoints.service.utils import convert_file_tree_to_nodes

from core.connectivity.instance_factory import instance_factory
from core.connectivity.agents import available_flavours
from core.management.instances.models import Instance
from core.management.instances import AbstractInstanceManager
from core.management.policies import AbstractPolicyManager
from core.management.policies import Policy
from core.management.users import AbstractUserManager

from core.management.users.models import UserCreate

from api.v0_1.endpoints.service.auth import decode_token, is_user_admin

admin_router = APIRouter(prefix='/admin', tags=["Administration"])


@admin_router.get("/test", dependencies=[Depends(decode_token)])
async def admin_route(user: dict = Depends(decode_token)) -> JSONResponse:
    """
    A test route that can only be accessed by administrators.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Welcome, administrator!"})


@admin_router.get(
    "/user",
    response_model=User,
    summary="Get user information",
    description="Retrieve user information by username.",
    response_description="User information",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(decode_token)]
)
async def get_user_(
        username: str = Query(..., description="Username of the user to retrieve"),
        user: dict = Depends(decode_token),
        user_manager: 'AbstractUserManager' = Depends(get_user_manager)
) -> User:
    """
    Retrieve user information.

    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Retrieve the users user_uuid
    try:
        uuid = user_manager.get_user_uuid(username)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Retrieve the user info
    return user_manager.get_user(uuid)


@admin_router.put(
    "/user/",
    response_model=AddUserResponse,
    summary="Add a new user",
    description=(
            "Creates a new user in the system. The new user is added in the external "
            "authentication service (e.g., Keycloak) and their policy file is created. "
            "If any part fails, the system performs a rollback."
    ),
    response_description="Details of the created user",
    dependencies=[Depends(decode_token)]
)
async def add_user_(
        user_data: AddUserRequest,  # Request body containing username, email, roles
        user: dict = Depends(decode_token),
        user_manager: 'AbstractUserManager' = Depends(get_user_manager),
        policy_manager: 'AbstractPolicyManager' = Depends(get_policy_manager)
) -> AddUserResponse:
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    user_create = UserCreate(
        username=user_data.username,
        email=user_data.email,
        roles=user_data.roles,
        password="default_password"
    )

    # Check if the user already exists
    try:
        if user_manager.get_user_uuid(user_create.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists."
            )
    except KeyError:
        pass

    # Create the user in the external authentication service
    user_manager.create_user(user_create)
    uuid = user_manager.get_user_uuid(user_data.username)

    # Add a policy file if successfully created
    if not policy_manager.create_user_policy_store(uuid):
        # If the policy manager fails to create the policy file, remove the user
        user_manager.delete_user(uuid)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user policy file. User not created"
        )

    user_details = user_manager.get_user(uuid)

    return AddUserResponse(success=True, details=user_details)


@admin_router.delete("/user/",
                     summary="Remove a user",
                     description="Removes a user from the system and deletes their policy store.",
                     response_description="Details of the removed user",
                     status_code=status.HTTP_200_OK,
                     response_model=RemoveUserResponse,
                     response_class=JSONResponse)
async def remove_user(username: str = Query(..., description="Username of the user to remove"),
                      user: dict = Depends(decode_token),
                      user_manager: AbstractUserManager = Depends(get_user_manager),
                      policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                      ) -> RemoveUserResponse:
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Remove user
    uuid = user_manager.get_user_uuid(username)
    user_details = user_manager.get_user(uuid)
    if not uuid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user_manager.delete_user(uuid):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to delete user.")

    if not policy_manager.remove_user_policy_store(uuid):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to remove user policy file.")

    return RemoveUserResponse(success=True, details=user_details)


@admin_router.get("/policies",
                  summary="Get policies filtered by the provided policy. If fields are empty, all relevant policies "
                          "are returned.",
                  description="Retrieve policies based on the provided filter.",
                  response_description="Filtered policies",
                  status_code=status.HTTP_200_OK,
                  response_model=GetPolicyResponse,
                  dependencies=[Depends(decode_token)]
                  )
async def get_policies(policy_filter: Policy = Depends(),
                       user: dict = Depends(decode_token),
                       policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                       user_manager: AbstractUserManager = Depends(get_user_manager)
                       ) -> GetPolicyResponse:
    """
    Retrieve policies based on the provided filter.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    if policy_filter is None:
        policy_filter = Policy(
            user_uuid=None,
            endpoint_uuid=None,
            resource=None,
            action=None
        )

    policies = policy_manager.filter_policies(policy_filter)
    if policies is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No policies found.")

    return GetPolicyResponse(success=True, details=policies)


@admin_router.put("/policy", dependencies=[Depends(decode_token)])
async def add_policy(new_policy: AddPolicyRequest = Depends(),
                     user_manager: AbstractUserManager = Depends(get_user_manager),
                     policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                     endpoint_manager: AbstractInstanceManager = Depends(get_instance_manager),
                     user: dict = Depends(decode_token)) -> AddPolicyResponse:
    """
    Add a policy.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Unpack the new policy
    username = new_policy.username
    access_point = new_policy.endpoint_name
    resource = new_policy.resource
    action = new_policy.action

    # Get the user uuid
    uuid = user_manager.get_user_uuid(username)
    # Convert access point name to uuid
    access_point_uuid = endpoint_manager.get_endpoint_uuid(access_point)

    # Create the new policy
    new_policy = Policy(
        user_uuid=uuid,
        endpoint_uuid=access_point_uuid,
        resource=resource,
        action=action
    )

    if user_manager.get_user(new_policy.user_uuid) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if endpoint_manager.get_endpoint_by_uuid(new_policy.endpoint_uuid) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access point not found")

    try:
        policy_manager.add_policies([new_policy])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to add policy. {e}")

    return AddPolicyResponse(success=True, details=[new_policy])


@admin_router.delete("/policy", dependencies=[Depends(decode_token)])
async def remove_policy(old_policy: RemovePolicyRequest = Depends(),
                        user_manager: AbstractUserManager = Depends(get_user_manager),
                        policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                        endpoint_manager: AbstractInstanceManager = Depends(get_instance_manager),
                        user: dict = Depends(decode_token)) -> RemovePolicyResponse:
    """
    Remove a policy.
    """
    # Check admin privileges
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Unpack the old policy
    username = old_policy.username
    access_point = old_policy.endpoint_name
    resource = old_policy.resource
    action = old_policy.action

    # Remove the policy
    old_policy = Policy(
        user_uuid=user_manager.get_user_uuid(username),
        endpoint_uuid=endpoint_manager.get_endpoint_uuid(access_point),
        resource=resource,
        action=action
    )

    try:
        policy_manager.remove_policy(old_policy)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to remove policy. {e}")

    return RemovePolicyResponse(success=True, details=[old_policy])


@admin_router.post("/endpoints/", dependencies=[Depends(decode_token)])
async def create_new_endpoint(
        config: InstanceCreate = Body(...),
        endpoint_manager: AbstractInstanceManager = Depends(get_instance_manager),
        policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
        token_payload: dict = Depends(decode_token)
) -> JSONResponse:
    """
    Add a new storage endpoint.
    Accepts JSON payload with a "flavour" field plus required fields for that flavour.
    """
    # Check admin privileges
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    flavour = config.flavour
    # Generate a stable UUID for the endpoint from its name
    access_point_uid = uuid5(NAMESPACE_DNS, config.access_point_name)

    # Convert the Pydantic model to a dict.
    config_dict = dict()
    config_dict['agent'] = config.dict(exclude={"flavour", 'access_point_name'})
    config_dict['flavour'] = flavour

    # Create the storage agent for the endpoint
    agent = instance_factory(config_dict)

    # Create the endpoint object
    new_endpoint = Instance(
        uuid=access_point_uid,
        name=config.access_point_name,
        flavour=flavour,
        agent=agent
    )

    # Register with the endpoint manager
    endpoint_manager.endpoints.append(new_endpoint)

    # Save the configuration
    endpoint_manager.save_configuration()

    # Add a policy so the creating user can administer the new endpoint
    user_uuid_str = token_payload.get("sub")
    user_uuid = UUID(user_uuid_str)
    new_admin_policy = Policy(
        user_uuid=user_uuid,
        endpoint_uuid=access_point_uid,
        resource='.*',
        action='admin'
    )

    # Add the admin policy for the endpoint to the policy manager
    try:
        if not policy_manager.add_policy(new_admin_policy):
            # If the policy manager fails to add the policy, remove the endpoint
            endpoint_manager.delete_endpoint(endpoint_manager.get_endpoint_by_uuid(access_point_uid))

            raise HTTPException(status_code=status.HTTP_500_BAD_REQUEST,
                                detail="Failed to add the administrator policy for the new endpoint.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to add the administrator policy for the new endpoint. {e}")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"detail": f"Instance '{new_endpoint.name}' created successfully."}
    )


@admin_router.delete("/endpoints/", dependencies=[Depends(decode_token)])
async def remove_endpoint(endpoint_uid: str = Query(..., description="UID of the endpoint to remove"),
                          endpoint_manager: AbstractInstanceManager = Depends(get_instance_manager),
                          policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                          user: dict = Depends(decode_token)) -> JSONResponse:
    """
    Remove a storage endpoint.
    """
    # Check admin privileges
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Admin privileges required")

    # Convert endpoint_uid to UUID
    try:
        endpoint_uid = UUID(endpoint_uid)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid endpoint UID format. Must be a valid UUID.")

    try:
        endpoint_manager.get_endpoint_by_uuid(endpoint_uid)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Access point {endpoint_uid} not found.")

    # Delete the endpoint from the manager
    old_endpoint = Instance(
        uuid=endpoint_uid,
        name=endpoint_manager.get_endpoint_by_uuid(endpoint_uid).name,
        flavour=endpoint_manager.get_endpoint_by_uuid(endpoint_uid).flavour,
        agent=endpoint_manager.get_endpoint_by_uuid(endpoint_uid).agent
    )

    # Delete the endpoint
    try:
        endpoint_manager.delete_endpoint(old_endpoint)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Failed to remove endpoint: {e}")

    # Delete policies associated with the endpoint
    try:
        policies = policy_manager.get_endpoint_policies(old_endpoint.uuid)
        policy_manager.remove_policies(policies)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to remove policies for endpoint: {e}")

    return JSONResponse(content={"detail": f"Instance '{endpoint_uid}' removed."})


# Dashboard Data Instances

@admin_router.get("/dashboard/policy-management",
                  response_model=PolicyManagementData,
                  summary="Get policy management dashboard data",
                  description="Retrieve file trees and endpoint data for policy management interface.",
                  dependencies=[Depends(decode_token)])
async def get_policy_management_data(
        token_payload: dict = Depends(decode_token),
        user_manager: AbstractUserManager = Depends(get_user_manager),
        policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
        endpoint_manager: AbstractInstanceManager = Depends(get_instance_manager)
) -> PolicyManagementData:
    """
    Get aggregated data for policy management dashboard.
    """
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    username = token_payload.get("preferred_username")
    uuid = user_manager.get_user_uuid(username)

    policy = Policy(
        user_uuid=uuid,
        action='admin'
    )

    # Get all endpoints the user has 'admin' access to
    admin_policies = policy_manager.filter_policies(policy)
    admin_endpoint_uuids = list(set(policy.endpoint_uuid for policy in admin_policies))
    admin_endpoints = endpoint_manager.get_endpoints_by_uuid(admin_endpoint_uuids)

    assets = {}
    # Populate the file trees for each endpoint
    for endpoint in admin_endpoints:
        # Partition the file type based on the policy
        file_tree = endpoint.agent.partition_file_tree_by_access(
            policy_manager, uuid, endpoint.uuid, 'admin'
        )['admin']
        assets[endpoint.name] = convert_file_tree_to_nodes(file_tree)

    return PolicyManagementData(assets=assets, endpoints=admin_endpoints)


@admin_router.get("/dashboard/user-management",
                  response_model=UserManagementData,
                  summary="Get user management dashboard data",
                  description="Retrieve all users with their file trees for user management interface.",
                  dependencies=[Depends(decode_token)])
async def get_user_management_data(
        token_payload: dict = Depends(decode_token),
        user_manager: AbstractUserManager = Depends(get_user_manager),
        policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
        endpoint_manager: AbstractInstanceManager = Depends(get_instance_manager)
) -> UserManagementData:
    """
    Get aggregated data for user management dashboard.
    """
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    users = user_manager.get_all_users()
    file_trees = {}

    # Loop through users to build file trees based on access levels
    for user in users:
        # Get all storage endpoints the user has access to
        endpoint_uuids = list(set(policy.endpoint_uuid for policy in policy_manager.get_user_policies(user.uuid)))
        endpoints = endpoint_manager.get_endpoints_by_uuid(endpoint_uuids)

        user_trees = {}

        # Loop through each storage endpoint and filter its file tree
        for endpoint in endpoints:
            f_trees = endpoint.agent.partition_file_tree_by_access(
                policy_manager, user.uuid, endpoint.uuid, ['read', 'write', 'admin']
            )

            if f_trees is not None:
                user_trees[(endpoint.name, str(endpoint.uuid))] = {
                    access_type: convert_file_tree_to_nodes(tree) 
                    for access_type, tree in f_trees.items()
                }

        file_trees[str(user.uuid)] = user_trees

    # Include the required form metadata for the models
    required_models = [
        "AddUserRequest",
        "AddUserResponse", 
        "RemoveUserResponse"
    ]

    json_registry = {
        name: {
            "endpoint": entry["endpoint"],
            "schema": entry["model_class"].model_json_schema()
        }
        for name, entry in model_registry.items()
        if name in required_models
    }

    return UserManagementData(users=users, file_trees=file_trees, models=json_registry)


@admin_router.get("/dashboard/endpoint-management",
                  response_model=InstanceManagementData,
                  summary="Get endpoint management dashboard data",
                  description="Retrieve endpoint configurations and available flavours.",
                  dependencies=[Depends(decode_token)])
async def get_endpoint_management_data(
        token_payload: dict = Depends(decode_token),
        endpoint_manager: AbstractInstanceManager = Depends(get_instance_manager)
) -> InstanceManagementData:
    """
    Get aggregated data for endpoint management dashboard.
    """
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Gather endpoint details
    endpoints = endpoint_manager.endpoints

    configs = {
        endpoint.name: (str(endpoint.uuid), endpoint.config(secrets=False))
        for endpoint in endpoints
    }

    return InstanceManagementData(endpoints=configs, flavours=available_flavours)


@admin_router.get("/dashboard/asset-management",
                  response_model=AssetManagementData,
                  summary="Get asset management dashboard data",
                  description="Retrieve file trees and endpoint mappings for asset management interface.",
                  dependencies=[Depends(decode_token)])
async def get_asset_management_data(
        token_payload: dict = Depends(decode_token),
        policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
        endpoint_manager: AbstractInstanceManager = Depends(get_instance_manager)
) -> AssetManagementData:
    """
    Get aggregated data for asset management dashboard.
    """
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Retrieve the user's user_uuid from the token payload
    uuid = token_payload.get("sub")

    # Get all storage access points the user has read access to
    endpoint_uuids = list(
        set(policy.endpoint_uuid for policy in policy_manager.get_user_policies(uuid))
    )
    endpoints = endpoint_manager.get_endpoints_by_uuid(endpoint_uuids)

    file_trees = {}
    for endpoint in endpoints:
        f_trees = endpoint.agent.partition_file_tree_by_access(
            policy_manager, uuid, endpoint.uuid, ["read", "write"]
        )
        if f_trees is not None:
            file_trees[str(endpoint.uuid)] = {
                access_type: convert_file_tree_to_nodes(tree)
                for access_type, tree in f_trees.items()
            }

    # Convert to simple string → string mapping for JSON encoding
    endpoint_names = {endpoint.name: str(endpoint.uuid) for endpoint in endpoints}

    return AssetManagementData(assets=file_trees, endpoints=endpoint_names)
