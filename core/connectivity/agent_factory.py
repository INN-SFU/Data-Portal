from core.connectivity.agent import Agent
from core.connectivity.agents import available_flavours


# Factory for instantiating the correct Agent based on configuration
def new_endpoint(flavour: str, config: dict) -> Agent:
    try:
        return available_flavours[flavour](**config)
    except KeyError:
        raise ValueError(f"Unsupported storage flavour: {flavour}")
