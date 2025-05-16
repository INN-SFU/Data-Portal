import json
import logging
import os
from typing import Union
from uuid import UUID

from core.management.endpoints.abstract_endpoint_manager import AbstractEndpointManager
from core.management.endpoints.models import Endpoint

logger = logging.getLogger(__name__)


class EndpointManager(AbstractEndpointManager):

    def __init__(self):
        super().__init__()
        self._configuration_files = os.getenv("ENDPOINT_CONFIGS")

    def save_configuration(self) -> bool:

        for endpoint in self.endpoints:
            endpoint_config_json = os.path.join(
                self._configuration_files, f"{str(endpoint.uuid)}.json"
            )

            # Get the configuration of the endpoint
            config = endpoint.config(secrets=True)

            with open(endpoint_config_json, 'w') as f:
                json.dump(config, f, indent=4)

        return True

    def delete_configuration(self, endpoint: Endpoint) -> bool:
        endpoint_config_json = os.path.join(
            self._configuration_files, f"{endpoint.uuid.__str__()}.json"
        )

        if os.path.exists(endpoint_config_json):
            os.remove(endpoint_config_json)

        return True
