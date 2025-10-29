"""
Storage Instance Management API Endpoints

Handles storage instance CRUD operations and instance-related dashboard data.
All endpoints require admin privileges as instances control system storage access.
"""

import os
from pathlib import Path
from uuid import uuid5, NAMESPACE_DNS, UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import JSONResponse

from core.injection import get_instance_manager, get_policy_manager
from core.connectivity.instance_factory import instance_factory
from core.connectivity.agents import available_flavours
from core.management.instances.models import Instance
from core.management.instances import AbstractInstanceManager
from core.management.policies import AbstractPolicyManager, Policy

from ..auth_dependencies import require_admin
from .models import InstanceCreate, InstanceManagementData

instances_router = APIRouter(prefix='/instances', tags=["Storage Instance Management"])


def _get_issuer_config():
    """
    Load Storage Issuer configuration from environment.

    The Storage Issuer service generates JWT tokens for file access. This function
    loads the Issuer's URL and API key from backend environment variables, keeping
    these credentials internal to the backend (not exposed to users).

    Environment Variables:
        STORAGE_ISSUER_URL: Issuer service URL (e.g., http://storage-issuer:8001)
        STORAGE_ISSUER_API_KEY_FILE: Path to API key secret file
        STORAGE_ISSUER_API_KEY: Fallback API key from env var

    Returns:
        dict: {
            'issuer_url': str,
            'issuer_api_key': str
        }

    Raises:
        HTTPException: 500 if configuration is missing or invalid
    """
    issuer_url = os.getenv("STORAGE_ISSUER_URL")
    if not issuer_url:
        raise HTTPException(
            status_code=500,
            detail="STORAGE_ISSUER_URL not configured in backend"
        )

    # Try to load from secret file first, fall back to env var
    api_key_file = os.getenv("STORAGE_ISSUER_API_KEY_FILE")
    issuer_api_key = None

    if api_key_file:
        try:
            issuer_api_key = Path(api_key_file).read_text().strip()
        except Exception:
            pass  # Fall back to env var

    if not issuer_api_key:
        issuer_api_key = os.getenv("STORAGE_ISSUER_API_KEY")

    if not issuer_api_key:
        raise HTTPException(
            status_code=500,
            detail="STORAGE_ISSUER_API_KEY not configured in backend"
        )

    return {
        "issuer_url": issuer_url,
        "issuer_api_key": issuer_api_key
    }


@instances_router.get(
    "/",
    summary="List all storage instances",
    description="Retrieve list of all configured storage instances with their details."
)
async def list_instances(
    admin_user: dict = Depends(require_admin),
    instance_manager: AbstractInstanceManager = Depends(get_instance_manager)
) -> JSONResponse:
    """
    Get list of all storage instances (admin only).
    
    Args:
        admin_user: Current user (must have admin privileges)
        instance_manager: Instance manager dependency
        
    Returns:
        JSONResponse: List of instances with their configurations
    """
    instances = instance_manager.instances
    
    instance_list = []
    for instance in instances:
        instance_data = {
            "uuid": str(instance.uuid),
            "name": instance.name,
            "flavour": instance.flavour,
            "config": instance.config(secrets=False)  # Don't expose secrets
        }
        instance_list.append(instance_data)
    
    return JSONResponse(
        status_code=200,
        content={"instances": instance_list}
    )


@instances_router.get(
    "/{instance_id}",
    summary="Get storage instance details",
    description="Retrieve detailed information about a specific storage instance."
)
async def get_instance(
    instance_id: str,
    admin_user: dict = Depends(require_admin),
    instance_manager: AbstractInstanceManager = Depends(get_instance_manager)
) -> JSONResponse:
    """
    Get details for a specific storage instance (admin only).
    
    Args:
        instance_id: UUID of the instance to retrieve
        admin_user: Current user (must have admin privileges)
        instance_manager: Instance manager dependency
        
    Returns:
        JSONResponse: Instance details and configuration
        
    Raises:
        HTTPException: 404 if instance not found
        HTTPException: 400 if invalid UUID format
    """
    try:
        instance_uuid = UUID(instance_id)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid instance ID format. Must be a valid UUID."
        )
    
    try:
        instance = instance_manager.get_instance_by_uuid(instance_uuid)
    except ValueError:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    return JSONResponse(
        status_code=200,
        content={
            "uuid": str(instance.uuid),
            "name": instance.name,
            "flavour": instance.flavour,
            "config": instance.config(secrets=False)
        }
    )


@instances_router.post(
    "/",
    summary="Create a new storage instance",
    description="Add a new storage instance configuration and automatically grant admin access to creator.",
    status_code=status.HTTP_201_CREATED
)
async def create_instance(
    config: InstanceCreate = Body(...),
    admin_user: dict = Depends(require_admin),
    instance_manager: AbstractInstanceManager = Depends(get_instance_manager),
    policy_manager: AbstractPolicyManager = Depends(get_policy_manager)
) -> JSONResponse:
    """
    Create a new storage instance (admin only).
    
    Accepts JSON payload with flavour and configuration details.
    Automatically grants admin access to the creating user.
    
    Args:
        config: Instance creation configuration
        admin_user: Current user (must have admin privileges)
        instance_manager: Instance manager dependency
        policy_manager: Policy manager dependency
        
    Returns:
        JSONResponse: Success message with created instance details
        
    Raises:
        HTTPException: 400 if configuration invalid
        HTTPException: 500 if policy creation fails
    """

    name_value = getattr(config, "instance_name", None) or getattr(config, "name", None)
    if not name_value:
        raise HTTPException(status_code=422,
                            detail="'instance_name' or 'name' field is required")
    flavour = config.flavour
    
    # Generate stable UUID for the instance from its name
    instance_uuid = uuid5(NAMESPACE_DNS, name_value)

    # Convert Pydantic model to dict for instance factory
    agent_cfg = config.dict(exclude={"flavour", "instance_name", "name"})

    # Inject the generated instance_uuid into agent config (for agents that need it)
    agent_cfg["instance_uuid"] = str(instance_uuid)

    # For POSIX agents, inject backend-internal issuer configuration
    # This keeps Storage Issuer credentials private (not user-provided)
    if flavour == "posix":
        issuer_config = _get_issuer_config()
        agent_cfg["issuer_url"] = issuer_config["issuer_url"]
        agent_cfg["issuer_api_key"] = issuer_config["issuer_api_key"]

    config_dict = {"agent": agent_cfg, "flavour": flavour}

    # Create the storage agent for the instance
    try:
        agent = instance_factory(config_dict)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create storage agent: {str(e)}"
        )

    # Create the instance object
    new_instance = Instance(
        uuid=instance_uuid,
        name=config.instance_name,
        flavour=flavour,
        agent=agent
    )

    # Register with the instance manager
    instance_manager.instances.append(new_instance)

    # Save the configuration
    try:
        instance_manager.save_configuration()
    except Exception as e:
        # Remove from instances list if save fails
        instance_manager.instances.remove(new_instance)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save instance configuration: {str(e)}"
        )

    # Add admin policy for the creating user
    user_uuid_str = admin_user.get("sub")
    user_uuid = UUID(user_uuid_str)
    new_admin_policy = Policy(
        user_uuid=user_uuid,
        instance_uuid=instance_uuid,
        resource='.*',
        action='admin'
    )

    # Add the admin policy
    try:
        if not policy_manager.add_policy(new_admin_policy):
            # If policy fails, remove the instance
            instance_manager.delete_instance(new_instance)
            raise HTTPException(
                status_code=500,
                detail="Failed to add administrator policy for new instance"
            )
    except ValueError as e:
        # If policy fails, remove the instance
        instance_manager.delete_instance(new_instance)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to add administrator policy: {str(e)}"
        )

    return JSONResponse(
        status_code=201,
        content={
            "message": f"Instance '{new_instance.name}' created successfully",
            "instance": {
                "uuid": str(new_instance.uuid),
                "name": new_instance.name,
                "flavour": new_instance.flavour
            }
        }
    )


@instances_router.delete(
    "/{instance_id}",
    summary="Remove a storage instance",
    description="Remove a storage instance and all its associated policies."
)
async def delete_instance(
    instance_id: str,
    admin_user: dict = Depends(require_admin),
    instance_manager: AbstractInstanceManager = Depends(get_instance_manager),
    policy_manager: AbstractPolicyManager = Depends(get_policy_manager)
) -> JSONResponse:
    """
    Remove a storage instance and cleanup associated policies (admin only).
    
    Args:
        instance_id: UUID of the instance to remove
        admin_user: Current user (must have admin privileges)
        instance_manager: Instance manager dependency
        policy_manager: Policy manager dependency
        
    Returns:
        JSONResponse: Success message
        
    Raises:
        HTTPException: 400 if invalid UUID format
        HTTPException: 404 if instance not found
        HTTPException: 400 if deletion fails
    """
    try:
        instance_uuid = UUID(instance_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid instance ID format. Must be a valid UUID."
        )

    # Get instance details before deletion
    try:
        instance = instance_manager.get_instance_by_uuid(instance_uuid)
    except ValueError:
        raise HTTPException(status_code=404, detail="Instance not found")

    # Create instance object for deletion
    instance_to_delete = Instance(
        uuid=instance_uuid,
        name=instance.name,
        flavour=instance.flavour,
        agent=instance.agent
    )

    # Delete the instance
    try:
        instance_manager.delete_instance(instance_to_delete)
    except KeyError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to remove instance: {str(e)}"
        )

    # Delete associated policies
    try:
        policies = policy_manager.get_instance_policies(instance_uuid)
        if policies:
            policy_manager.remove_policies(policies)
    except ValueError as e:
        # Log warning but don't fail the deletion
        # The instance is already removed
        pass

    return JSONResponse(
        status_code=200,
        content={"message": f"Instance '{instance_id}' removed successfully"}
    )


@instances_router.get(
    "/dashboard",
    response_model=InstanceManagementData,
    summary="Get instance management dashboard data",
    description="Admin dashboard with instance configurations and available flavours."
)
async def get_instance_dashboard(
    admin_user: dict = Depends(require_admin),
    instance_manager: AbstractInstanceManager = Depends(get_instance_manager)
) -> InstanceManagementData:
    """
    Get instance management dashboard data (admin only).
    
    Provides instance configurations and available storage flavours
    for the management interface.
    
    Args:
        admin_user: Current user (must have admin privileges)
        instance_manager: Instance manager dependency
        
    Returns:
        InstanceManagementData: Dashboard data with instances and flavours
    """
    instances = instance_manager.instances

    # Build configuration data (without secrets)
    configs = {
        instance.name: (str(instance.uuid), instance.config(secrets=False))
        for instance in instances
    }

    return InstanceManagementData(instances=configs, flavours=available_flavours)