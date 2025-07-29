import json
import logging
import os
from typing import Union
from uuid import UUID

from core.management.instances.abstract_instance_manager import AbstractInstanceManager
from core.management.instances.models import Instance

logger = logging.getLogger(__name__)


class InstanceManager(AbstractInstanceManager):

    def __init__(self):
        super().__init__()
        self._configuration_files = os.getenv("INSTANCE_CONFIGS")

    def save_configuration(self) -> bool:

        for instance in self.instances:
            instance_config_json = os.path.join(
                self._configuration_files, f"{str(instance.uuid)}.json"
            )

            # Get the configuration of the instance
            config = instance.config(secrets=True)

            with open(instance_config_json, 'w') as f:
                json.dump(config, f, indent=4)

        return True

    def delete_configuration(self, instance: Instance) -> bool:
        instance_config_json = os.path.join(
            self._configuration_files, f"{instance.uuid.__str__()}.json"
        )

        if os.path.exists(instance_config_json):
            os.remove(instance_config_json)

        return True
