import json
import logging
import os
from pathlib import Path
from typing import Union
from uuid import UUID

from core.management.instances.abstract_instance_manager import AbstractInstanceManager
from core.management.instances.models import Instance

logger = logging.getLogger("instance-manager")


class InstanceManager(AbstractInstanceManager):

    def __init__(self):
        super().__init__()
        self._configuration_files = os.getenv("INSTANCE_CONFIGS")

    def save_configuration(self) -> bool:

        for instance in self.instances:
            instance_config_json = Path(self._configuration_files) / f"{str(instance.uuid)}.json"

            try:
                # Get the configuration of the instance
                config = instance.config(secrets=True)

                with open(instance_config_json, 'w') as f:
                    json.dump(config, f, indent=4)
                
                logger.info(f"Successfully saved configuration for instance {instance.uuid}")
            except Exception as e:
                logger.error(f"Failed to save configuration for instance {instance.uuid}: {str(e)}")
                raise

        return True

    def delete_configuration(self, instance: Instance) -> bool:
        instance_config_json = Path(self._configuration_files) / f"{instance.uuid.__str__()}.json"

        if instance_config_json.exists():
            try:
                instance_config_json.unlink()
                logger.info(f"Successfully deleted configuration file for instance {instance.uuid}")
            except Exception as e:
                logger.error(f"Failed to delete configuration file {instance_config_json}: {str(e)}")
                raise
        else:
            logger.warning(f"Configuration file not found for instance {instance.uuid}: {instance_config_json}")

        return True
