import os
from fastapi import HTTPException, status
from core.management.instances import AbstractInstanceManager
from core.management.users import AbstractUserManager
from core.management.policies import AbstractPolicyManager

# Global manager instances - created lazily on first access
_user_manager = None
_instance_manager = None
_policy_manager = None


def get_user_manager() -> AbstractUserManager:
    """
    Returns the user manager instance, creating it lazily on first access.
    """
    global _user_manager
    if _user_manager is None:
        # Lazy import to avoid circular dependencies
        from core.settings.managers.users.keycloak import KeycloakUserManager

        # Check if required environment variables are available
        print("DEBUG: Initializing user manager...")
        admin_secret = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET")
        print(f"DEBUG: Admin secret available: {'YES' if admin_secret else 'NO'}")
        print(f"DEBUG: Admin secret length: {len(admin_secret) if admin_secret else 0}")
        print(f"DEBUG: Admin secret preview: {admin_secret[:8]}..." if admin_secret else "DEBUG: Admin secret is None/empty")

        print(f"DEBUG: KEYCLOAK_REALM: {os.getenv('KEYCLOAK_REALM')}")
        print(f"DEBUG: KEYCLOAK_ADMIN_CLIENT_ID: {os.getenv('KEYCLOAK_ADMIN_CLIENT_ID')}")
        print(f"DEBUG: KEYCLOAK_DOMAIN: {os.getenv('KEYCLOAK_DOMAIN')}")

        if not admin_secret:
            print("ERROR: Admin client secret not available during user manager initialization")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Keycloak admin client secret not available. Please wait for application startup to complete."
            )

        print("DEBUG: Creating KeycloakUserManager instance...")
        _user_manager = KeycloakUserManager(
            realm_name=os.getenv("KEYCLOAK_REALM"),
            client_id=os.getenv("KEYCLOAK_ADMIN_CLIENT_ID"),
            client_secret=admin_secret,
            base_url=os.getenv("KEYCLOAK_DOMAIN")
        )
        print("DEBUG: KeycloakUserManager instance created successfully")

    return _user_manager


def get_policy_manager() -> AbstractPolicyManager:
    """
    Returns the policy manager instance, creating it lazily on first access.
    Policies are loaded on-demand rather than all upfront.
    """
    global _policy_manager
    if _policy_manager is None:
        # Lazy import to avoid circular dependencies
        from core.settings.managers.policies.casbin.CasbinPolicyManager import CasbinPolicyManager

        # Initialize with empty UUID list - policies will be loaded on-demand
        _policy_manager = CasbinPolicyManager(uuids=[])

    return _policy_manager


def get_instance_manager() -> AbstractInstanceManager:
    """
    Returns the instance manager instance, creating it lazily on first access.
    """
    global _instance_manager
    if _instance_manager is None:
        # Lazy import to avoid circular dependencies
        from core.settings.managers.instances.InstanceManager import InstanceManager

        _instance_manager = InstanceManager()

        # Load instance configurations if available
        instance_configs_dir = os.getenv("INSTANCE_CONFIGS")
        if instance_configs_dir and os.path.exists(instance_configs_dir):
            import json
            from uuid import UUID
            from core.connectivity.instance_factory import instance_factory
            from core.management.instances.models import Instance

            config_files = [f for f in os.listdir(instance_configs_dir) if f.endswith('.json')]
            for file in config_files:
                uuid = file.split(".")[0]
                config_path = f"{instance_configs_dir}/{file}"

                with open(config_path) as f:
                    instance_config = json.load(f)

                name = instance_config["name"]
                config_data = {
                    "flavour": instance_config["flavour"],
                    "agent": instance_config["agent"]
                }

                # Create the instance agent
                instance = instance_factory(config_data)

                # Create the instance object
                new_instance = Instance(
                    uuid=UUID(uuid),
                    name=name,
                    flavour=config_data["flavour"],
                    agent=instance
                )

                # Add the instance to the instance manager
                _instance_manager.instances.append(new_instance)

    return _instance_manager
