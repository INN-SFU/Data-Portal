from .users import user_manager
from .policies import CasbinPolicyManager
from .endpoints import endpoint_manager

# Lazy initialization of policy manager
_policy_manager = None

def get_policy_manager():
    """Get the policy manager, initializing it if needed."""
    global _policy_manager
    if _policy_manager is None:
        try:
            # Get uuids from the user manager
            uuids = user_manager.get_user_uuids()
            _policy_manager = CasbinPolicyManager(uuids)
        except Exception as e:
            print(f"Warning: Could not initialize policy manager with user UUIDs: {e}")
            # Initialize with empty uuids as fallback
            _policy_manager = CasbinPolicyManager([])
    return _policy_manager

# For backward compatibility, provide policy_manager access
# This will be initialized on first access
class PolicyManagerProxy:
    def __getattr__(self, name):
        return getattr(get_policy_manager(), name)

policy_manager = PolicyManagerProxy()
