from core.connectivity.abstract_storage_agent import AbstractStorageAgent
from core.connectivity.agents import available_flavours


# Factory for instantiating the correct AbstractStorageAgent based on configuration
def new_endpoint(flavour: str, config: dict) -> AbstractStorageAgent:
    try:
        return available_flavours[flavour](**config)
    except KeyError:
        raise ValueError(f"Unsupported storage flavour: {flavour}")
