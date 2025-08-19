import os
import json
import logging
from uuid import UUID

from core.connectivity.instance_factory import instance_factory
from core.management.instances.models import Instance
from .InstanceManager import InstanceManager

logger = logging.getLogger('instance-manager')
instance_manager = InstanceManager()

# Loop through the instance configuration files and create the instance agents
for file in os.listdir(os.getenv("INSTANCE_CONFIGS")):
    uuid = file.split(".")[0]
    with open(f"{os.getenv('INSTANCE_CONFIGS')}/{file}") as f:
        instance_config = json.load(f)

    name = instance_config["name"]
    instance_config = {
        "flavour": instance_config["flavour"],
        "agent": instance_config["agent"]
    }

    # Create the instance agent
    instance = instance_factory(instance_config)

    # Create the instance object
    new_instance = Instance(
        uuid=UUID(uuid),
        name=name,
        flavour=instance_config["flavour"],
        agent=instance
    )

    # Set the agent for the instance
    new_instance.agent = instance

    # Add the instance to the instance manager
    instance_manager.instances.append(new_instance)
