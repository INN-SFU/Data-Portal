from core.management.endpoints import AbstractEndpointManager
from core.management.users import AbstractUserManager
from core.management.policies import AbstractPolicyManager

from core.settings.managers import user_manager
from core.settings.managers import policy_manager
from core.settings.managers import endpoint_manager


def get_user_manager() -> AbstractUserManager:
    """
    Returns the user manager instance.
    """
    return user_manager


def get_policy_manager() -> AbstractPolicyManager:
    """
    Returns the policy manager instance.
    """
    return policy_manager


def get_endpoint_manager() -> AbstractEndpointManager:
    """
    Returns the endpoint manager instance.
    """
    return endpoint_manager
