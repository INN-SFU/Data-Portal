import os
import json
from uuid import UUID

from core.connectivity.agent_factory import new_endpoint
from .EndpointManager import EndpointManager

endpoint_manager = EndpointManager()

# Loop through the endpoint configuration files and create the endpoint agents
for file in os.listdir(os.getenv("ENDPOINT_CONFIGS")):
    uid = file.split(".")[0]
    with open(f"{os.getenv('ENDPOINT_CONFIGS')}/{file}") as f:
        endpoint_config = json.load(f)

    # Create the endpoint agent
    endpoint = new_endpoint(endpoint_config["flavour"], endpoint_config["config"])

    uid = UUID(uid)

    endpoint_manager.endpoints[uid] = endpoint
