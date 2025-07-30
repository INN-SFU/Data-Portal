from core.management.instances import AbstractInstanceManager
from core.management.users import AbstractUserManager
from core.management.policies import AbstractPolicyManager

from core.settings.managers import user_manager
from core.settings.managers import policy_manager
from core.settings.managers import instance_manager


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


def get_instance_manager() -> AbstractInstanceManager:
    """
    Returns the instance manager instance.
    """
    return instance_manager
