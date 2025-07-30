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
from .utils import convert_file_tree_to_dict

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
                     instance_manager: AbstractInstanceManager = Depends(get_instance_manager),
                     user: dict = Depends(decode_token)) -> AddPolicyResponse:
    """
    Add a policy.
    """
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Unpack the new policy
    username = new_policy.username
    instance_name = new_policy.instance_name
    resource = new_policy.resource
    action = new_policy.action

    # Get the user uuid
    uuid = user_manager.get_user_uuid(username)
    # Convert access point name to uuid
    instance_uuid = instance_manager.get_instance_uuid(instance_name)

    # Create the new policy
    new_policy = Policy(
        user_uuid=uuid,
        instance_uuid=instance_uuid,
        resource=resource,
        action=action
    )

    if user_manager.get_user(new_policy.user_uuid) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if instance_manager.get_instance_by_uuid(new_policy.instance_uuid) is None:
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
                        instance_manager: AbstractInstanceManager = Depends(get_instance_manager),
                        user: dict = Depends(decode_token)) -> RemovePolicyResponse:
    """
    Remove a policy.
    """
    # Check admin privileges
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Unpack the old policy
    username = old_policy.username
    instance_name = old_policy.instance_name
    resource = old_policy.resource
    action = old_policy.action

    # Remove the policy
    old_policy = Policy(
        user_uuid=user_manager.get_user_uuid(username),
        instance_uuid=instance_manager.get_instance_uuid(instance_name),
        resource=resource,
        action=action
    )

    try:
        policy_manager.remove_policy(old_policy)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to remove policy. {e}")

    return RemovePolicyResponse(success=True, details=[old_policy])


@admin_router.post("/instances/", dependencies=[Depends(decode_token)])
async def create_new_instance(
        config: InstanceCreate = Body(...),
        instance_manager: AbstractInstanceManager = Depends(get_instance_manager),
        policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
        token_payload: dict = Depends(decode_token)
) -> JSONResponse:
    """
    Add a new storage instance.
    Accepts JSON payload with a "flavour" field plus required fields for that flavour.
    """
    # Check admin privileges
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    flavour = config.flavour
    # Generate a stable UUID for the instance from its name
    instance_uuid = uuid5(NAMESPACE_DNS, config.instance_name)

    # Convert the Pydantic model to a dict.
    config_dict = dict()
    config_dict['agent'] = config.dict(exclude={"flavour", 'access_point_name'})
    config_dict['flavour'] = flavour

    # Create the storage agent for the instance
    agent = instance_factory(config_dict)

    # Create the instance object
    new_instance = Instance(
        uuid=instance_uuid,
        name=config.access_point_name,
        flavour=flavour,
        agent=agent
    )

    # Register with the instance manager
    instance_manager.instances.append(new_instance)

    # Save the configuration
    instance_manager.save_configuration()

    # Add a policy so the creating user can administer the new instance
    user_uuid_str = token_payload.get("sub")
    user_uuid = UUID(user_uuid_str)
    new_admin_policy = Policy(
        user_uuid=user_uuid,
        instance_uuid=instance_uuid,
        resource='.*',
        action='admin'
    )

    # Add the admin policy for the instance to the policy manager
    try:
        if not policy_manager.add_policy(new_admin_policy):
            # If the policy manager fails to add the policy, remove the instance
            instance_manager.delete_instance(instance_manager.get_instance_by_uuid(instance_uuid))

            raise HTTPException(status_code=status.HTTP_500_BAD_REQUEST,
                                detail="Failed to add the administrator policy for the new instance.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to add the administrator policy for the new instance. {e}")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"detail": f"Instance '{new_instance.name}' created successfully."}
    )


@admin_router.delete("/instances/", dependencies=[Depends(decode_token)])
async def remove_instance(instance_uuid: str = Query(..., description="UID of the instance to remove"),
                          instance_manager: AbstractInstanceManager = Depends(get_instance_manager),
                          policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
                          user: dict = Depends(decode_token)) -> JSONResponse:
    """
    Remove a storage instance.
    """
    # Check admin privileges
    if not is_user_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Admin privileges required")

    # Convert instance_uid to UUID
    try:
        instance_uuid = UUID(instance_uuid)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid instance UID format. Must be a valid UUID.")

    try:
        instance_manager.get_instance_by_uuid(instance_uuid)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Access point {instance_uuid} not found.")

    # Delete the instance from the manager
    old_instance = Instance(
        uuid=instance_uuid,
        name=instance_manager.get_instance_by_uuid(instance_uuid).name,
        flavour=instance_manager.get_instance_by_uuid(instance_uuid).flavour,
        agent=instance_manager.get_instance_by_uuid(instance_uuid).agent
    )

    # Delete the instance
    try:
        instance_manager.delete_instance(old_instance)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Failed to remove instance: {e}")

    # Delete policies associated with the instance
    try:
        policies = policy_manager.get_instance_policies(old_instance.uuid)
        policy_manager.remove_policies(policies)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to remove policies for instance: {e}")

    return JSONResponse(content={"detail": f"Instance '{instance_uuid}' removed."})


# Dashboard Data Instances

@admin_router.get("/dashboard/policy-management",
                  response_model=PolicyManagementData,
                  summary="Get policy management dashboard data",
                  description="Retrieve file trees and instance data for policy management interface.",
                  dependencies=[Depends(decode_token)])
async def get_policy_management_data(
        token_payload: dict = Depends(decode_token),
        user_manager: AbstractUserManager = Depends(get_user_manager),
        policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
        instance_manager: AbstractInstanceManager = Depends(get_instance_manager)
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

    # Get all instances the user has 'admin' access to
    admin_policies = policy_manager.filter_policies(policy)
    instance_uuids = list(set(policy.instance_uuid for policy in admin_policies))
    admin_instances = instance_manager.get_instances_by_uuid(instance_uuids)

    assets = {}
    # Populate the file trees for each instance
    for instance in admin_instances:
        # Partition the file type based on the policy
        file_tree = instance.agent.partition_file_tree_by_access(policy_manager, uuid, instance.uuid, 'admin')['admin']
        assets[instance.name] = convert_file_tree_to_dict(file_tree)

    return PolicyManagementData(assets=assets, instances=admin_instances)


@admin_router.get("/dashboard/user-management",
                  response_model=UserManagementData,
                  summary="Get user management dashboard data",
                  description="Retrieve all users with their file trees for user management interface.",
                  dependencies=[Depends(decode_token)])
async def get_user_management_data(
        token_payload: dict = Depends(decode_token),
        user_manager: AbstractUserManager = Depends(get_user_manager),
        policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
        instance_manager: AbstractInstanceManager = Depends(get_instance_manager)
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
        # Get all storage instances the user has access to
        instance_uuids = list(set(policy.endpoint_uuid for policy in policy_manager.get_user_policies(user.uuid)))
        instances = instance_manager.get_instances_by_uuid(instance_uuids)

        user_trees = {}

        # Loop through each storage instance and filter its file tree
        for instance in instances:
            f_trees = instance.agent.partition_file_tree_by_access(policy_manager, user.uuid, instance.uuid,
                                                                   ['read', 'write', 'admin'])

            if f_trees is not None:
                user_trees[(instance.name, str(instance.uuid))] = {
                    access_type: convert_file_tree_to_dict(tree) 
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
            "instance": entry["instance"],
            "schema": entry["model_class"].model_json_schema()
        }
        for name, entry in model_registry.items()
        if name in required_models
    }

    return UserManagementData(users=users, file_trees=file_trees, models=json_registry)


@admin_router.get("/dashboard/instance-management",
                  response_model=InstanceManagementData,
                  summary="Get instance management dashboard data",
                  description="Retrieve instance configurations and available flavours.",
                  dependencies=[Depends(decode_token)])
async def get_instance_management_data(
        token_payload: dict = Depends(decode_token),
        instance_manager: AbstractInstanceManager = Depends(get_instance_manager)
) -> InstanceManagementData:
    """
    Get aggregated data for instance management dashboard.
    """
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Gather instance details
    instances = instance_manager.instances

    configs = {
        instance.name: (str(instance.uuid), instance.config(secrets=False))
        for instance in instances
    }

    return InstanceManagementData(instances=configs, flavours=available_flavours)


@admin_router.get("/dashboard/asset-management",
                  response_model=AssetManagementData,
                  summary="Get asset management dashboard data",
                  description="Retrieve file trees and instance mappings for asset management interface.",
                  dependencies=[Depends(decode_token)])
async def get_asset_management_data(
        token_payload: dict = Depends(decode_token),
        policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
        instance_manager: AbstractInstanceManager = Depends(get_instance_manager)
) -> AssetManagementData:
    """
    Get aggregated data for asset management dashboard.
    """
    if not is_user_admin(token_payload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Retrieve the user's user_uuid from the token payload
    uuid = token_payload.get("sub")

    # Get all storage access points the user has read access to
    instance_uuids = list(
        set(policy.instance_uuid for policy in policy_manager.get_user_policies(uuid))
    )
    instances = instance_manager.get_instances_by_uuid(instance_uuids)

    file_trees = {}
    for instance in instances:
        f_trees = instance.agent.partition_file_tree_by_access(policy_manager, uuid, instance.uuid, ["read", "write"])
        if f_trees is not None:
            file_trees[str(instance.uuid)] = {
                access_type: convert_file_tree_to_dict(tree)
                for access_type, tree in f_trees.items()
            }

    # Convert to simple string → string mapping for JSON encoding
    instance_names = {instance.name: str(instance.uuid) for instance in instances}

    return AssetManagementData(assets=file_trees, instances=instance_names)
