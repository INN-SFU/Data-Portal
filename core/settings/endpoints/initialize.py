import os
import json

from core.connectivity.agent_factory import new_endpoint


# Load configurations for the agents
configs = json.load(open(os.getenv('ACCESS_AGENT_CONFIG'), 'r'))

# Initialize the storage endpoints
storage_endpoints = {}
for endpoint,config in zip(configs.keys(),configs.values()):
    storage_endpoints[endpoint] = new_endpoint(config)
