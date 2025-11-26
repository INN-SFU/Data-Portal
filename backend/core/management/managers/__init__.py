# All managers are now handled via dependency injection in core.injection.managers
# This file exists only to avoid import errors from legacy code

from .policies import CasbinPolicyManager

# All managers now use lazy initialization via dependency injection
# Import core.injection.managers and use get_user_manager(), get_instance_manager(), get_policy_manager()
