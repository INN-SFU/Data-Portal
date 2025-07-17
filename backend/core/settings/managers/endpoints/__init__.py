import os
import json
import logging
from uuid import UUID

from core.connectivity.endpoint_factory import endpoint_factory
from core.management.endpoints.models import Endpoint
from .EndpointManager import EndpointManager

logger = logging.getLogger('endpoint-manager')
endpoint_manager = EndpointManager()

# Loop through the endpoint configuration files and create the endpoint agents
for file in os.listdir(os.getenv("ENDPOINT_CONFIGS")):
    uuid = file.split(".")[0]
    with open(f"{os.getenv('ENDPOINT_CONFIGS')}/{file}") as f:
        endpoint_config = json.load(f)

    name = endpoint_config["name"]
    endpoint_config = {
        "flavour": endpoint_config["flavour"],
        "agent": endpoint_config["agent"]
    }

    # Create the endpoint agent
    endpoint = endpoint_factory(endpoint_config)

    # Create the endpoint object
    new_endpoint = Endpoint(
        uuid=UUID(uuid),
        name=name,
        flavour=endpoint_config["flavour"],
        agent=endpoint
    )

    # Set the agent for the endpoint
    new_endpoint.agent = endpoint

    # Add the endpoint to the endpoint manager
    endpoint_manager.endpoints.append(new_endpoint)
