from abc import abstractmethod, ABC
from typing import Union, List
from uuid import UUID

from .models import Instance


class AbstractInstanceManager(ABC):

    def __init__(self) -> None:
        self._instances: List[Instance] = []

    @property
    def instances(self) -> list[Instance]:
        return self._instances

    def get_instances(self, access_points: set = None) -> dict[str, Instance]:
        """
        Get instances filtered by access point names.
        
        :param access_points: Set of instance names to filter by. If None, returns all instances.
        :return: Dictionary mapping instance names to Instance objects
        """
        if access_points is None:
            return {instance.name: instance for instance in self._instances}
        
        return {
            instance.name: instance 
            for instance in self._instances 
            if instance.name in access_points
        }

    @instances.setter
    def instances(self, instances: Union[Instance, list[Instance]]):
        if isinstance(instances, Instance):
            self.instances.append(instances)
        elif isinstance(instances, list):
            self.instances.extend(instances)
        else:
            raise TypeError("Expected Instance or list of Instances")

    @instances.deleter
    def instances(self):
        for instance in self.instances:
            # Close the agent including the connections
            instance.close()

        self._instances.clear()

    @abstractmethod
    def save_configuration(self) -> bool:
        pass

    @abstractmethod
    def delete_configuration(self, instance: Instance) -> bool:
        pass

    def get_instances_by_uuid(self, uuids: list[UUID]) -> list[Instance]:
        """
        Get instances by UUID.

        :param uuids: UUID or list of UUIDs to search for.
        :return: List of matching instances.
        """
        if isinstance(uuids, UUID):
            uuids = [uuids]

        matching_instances = [
            instance for instance in self.instances if instance.uuid in uuids
        ]

        return matching_instances

    def get_instance_uuid(self, instance_name: str) -> UUID:
        """
        Get the UUID of an instance by its name.

        :param instance_name: The name of the instance.
        :return: The UUID of the instance.
        """
        for instance in self.instances:
            if instance.name == instance_name:
                return instance.uuid

        raise ValueError(f"Instance with name '{instance_name}' not found.")

    def get_instance_by_uuid(self, uuid: UUID) -> Instance:
        """
        Get the instance by its UUID.

        :param uuid: The UUID of the instance.
        :return: The Instance object.
        """
        for instance in self.instances:
            if instance.uuid == uuid:
                return instance

        raise ValueError(f"Instance with UUID '{uuid}' not found.")

    def delete_instance(self, instance: Instance):
        """
        Delete an instance from the list and remove its configuration file.

        :param instance: The Instance object to delete.
        """
        if instance in self.instances:
            self.instances.remove(instance)
            self.delete_configuration(instance)
        else:
            raise KeyError(f"Instance {instance.uuid} not found.")
