import json
import os
import logging

from core.connectivity import new_endpoint

# Initialize the logger
logger = logging.getLogger("app")

storage_endpoints = {}
# Loop through the endpoint_url configuration files in the AGENT_CONFIGS directory and create an agent for each
for endpoint_file in os.listdir(os.getenv('ENDPOINT_CONFIGS')):
    with open(os.path.join(os.getenv('ENDPOINT_CONFIGS'), endpoint_file), 'r') as f:
        endpoint = json.load(f)
        endpoint_uid = endpoint_file.rstrip('.json')
    f.close()

    logger.warning("Creating endpoint: %s", endpoint_uid)

    try:
        if storage_endpoints[endpoint_uid] is not None:
            logger.info("Endpoint already exists: %s", endpoint_uid)
    except KeyError:
        storage_endpoints[endpoint_uid] = new_endpoint(endpoint["flavour"], endpoint["config"])

