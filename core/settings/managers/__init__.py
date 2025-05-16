from .users import user_manager
from .policies import CasbinPolicyManager
from .endpoints import endpoint_manager

# Get uuids from the user manager
uuids = user_manager.get_user_uuids()
policy_manager = CasbinPolicyManager(uuids)
