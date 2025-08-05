"""
User Management API Endpoints

Handles user CRUD operations using FastAPI dependency injection for authorization.
Supports admin-only, authenticated, and owner-or-admin access patterns.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse

from core.injection import get_user_manager, get_policy_manager, get_instance_manager
from core.management.users import AbstractUserManager
from core.management.policies import AbstractPolicyManager
from core.management.instances import AbstractInstanceManager
from core.management.users.models import UserCreate

from ..auth_dependencies import require_admin, get_current_user, require_user_owner_or_admin
from .models import (
    User, AddUserRequest, AddUserResponse, RemoveUserResponse,
    UserManagementData, model_registry
)
from .utils import convert_file_tree_to_dict

users_router = APIRouter(prefix='/users', tags=["User Management"])


@users_router.get(
    "/",
    response_model=list[User],
    summary="List all users",
    description="Retrieve list of all users in the system. Requires admin privileges."
)
async def list_users(
    admin_user: dict = Depends(require_admin),
    user_manager: AbstractUserManager = Depends(get_user_manager)
) -> list[User]:
    """Get list of all users (admin only)."""
    return user_manager.get_all_users()


@users_router.get(
    "/{username}",
    response_model=User,
    summary="Get user information",
    description="Users can view their own profile, admins can view any user."
)
async def get_user(
    username: str,
    request: Request,
    current_user: dict = Depends(require_user_owner_or_admin()),
    user_manager: AbstractUserManager = Depends(get_user_manager)
) -> User:
    """Get user details (owner or admin)."""
    try:
        uuid = user_manager.get_user_uuid(username)
        return user_manager.get_user(uuid)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")


@users_router.post(
    "/",
    response_model=AddUserResponse,
    summary="Create a new user",
    description="Creates user in auth service and sets up policies. Admin only.",
    status_code=status.HTTP_201_CREATED
)
async def create_user(
    user_data: AddUserRequest,
    admin_user: dict = Depends(require_admin),
    user_manager: AbstractUserManager = Depends(get_user_manager),
    policy_manager: AbstractPolicyManager = Depends(get_policy_manager)
) -> AddUserResponse:
    """Create new user with auth and policy setup (admin only)."""
    user_create = UserCreate(
        username=user_data.username,
        email=user_data.email,
        roles=user_data.roles,
        password="default_password"
    )

    # Check if user exists
    try:
        if user_manager.get_user_uuid(user_create.username):
            raise HTTPException(status_code=400, detail="User already exists")
    except KeyError:
        pass

    # Create user
    user_manager.create_user(user_create)
    uuid = user_manager.get_user_uuid(user_data.username)

    # Create policy store (rollback on failure)
    if not policy_manager.create_user_policy_store(uuid):
        user_manager.delete_user(uuid)
        raise HTTPException(status_code=500, detail="Failed to create user policy file")

    user_details = user_manager.get_user(uuid)
    return AddUserResponse(success=True, details=user_details)


@users_router.delete(
    "/{username}",
    response_model=RemoveUserResponse,
    summary="Remove a user",
    description="Users can delete their own account, admins can delete any user."
)
async def delete_user(
    username: str,
    request: Request,
    current_user: dict = Depends(require_user_owner_or_admin()),
    user_manager: AbstractUserManager = Depends(get_user_manager),
    policy_manager: AbstractPolicyManager = Depends(get_policy_manager)
) -> RemoveUserResponse:
    """Delete user and cleanup policies (owner or admin)."""
    try:
        uuid = user_manager.get_user_uuid(username)
        user_details = user_manager.get_user(uuid)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")

    if not user_manager.delete_user(uuid):
        raise HTTPException(status_code=400, detail="Failed to delete user")

    if not policy_manager.remove_user_policy_store(uuid):
        raise HTTPException(status_code=500, detail="Failed to remove user policy file")

    return RemoveUserResponse(success=True, details=user_details)


@users_router.get(
    "/me",
    response_model=User,
    summary="Get current user information",
    description="Retrieve information about the currently authenticated user."
)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    user_manager: AbstractUserManager = Depends(get_user_manager)
) -> User:
    """Get current user's own information (authenticated user)."""
    current_username = current_user.get("preferred_username")
    if not current_username:
        raise HTTPException(status_code=400, detail="Username not found in token")
    
    try:
        uuid = user_manager.get_user_uuid(current_username)
        return user_manager.get_user(uuid)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found in system")


@users_router.get(
    "/dashboard",
    response_model=UserManagementData,
    summary="Get user management dashboard data",
    description="Admin dashboard with all users and their access permissions."
)
async def get_user_dashboard(
    admin_user: dict = Depends(require_admin),
    user_manager: AbstractUserManager = Depends(get_user_manager),
    policy_manager: AbstractPolicyManager = Depends(get_policy_manager),
    instance_manager: AbstractInstanceManager = Depends(get_instance_manager)
) -> UserManagementData:
    """Get user management dashboard data (admin only)."""
    users = user_manager.get_all_users()
    file_trees = {}

    # Build file trees for each user based on their access
    for user in users:
        instance_uuids = list(set(
            policy.endpoint_uuid 
            for policy in policy_manager.get_user_policies(user.uuid)
        ))
        instances = instance_manager.get_instances_by_uuid(instance_uuids)
        user_trees = {}

        for instance in instances:
            f_trees = instance.agent.partition_file_tree_by_access(
                policy_manager, user.uuid, instance.uuid, ['read', 'write', 'admin']
            )
            if f_trees:
                user_trees[(instance.name, str(instance.uuid))] = {
                    access_type: convert_file_tree_to_dict(tree) 
                    for access_type, tree in f_trees.items()
                }

        file_trees[str(user.uuid)] = user_trees

    # Include form metadata
    required_models = ["AddUserRequest", "AddUserResponse", "RemoveUserResponse"]
    json_registry = {
        name: {
            "instance": entry["instance"],
            "schema": entry["model_class"].model_json_schema()
        }
        for name, entry in model_registry.items()
        if name in required_models
    }

    return UserManagementData(users=users, file_trees=file_trees, models=json_registry)