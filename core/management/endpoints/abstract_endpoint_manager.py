from abc import abstractmethod, ABC
from typing import Union, List
from uuid import UUID

from .models import Endpoint


class AbstractEndpointManager(ABC):

    def __init__(self) -> None:
        self._endpoints: List[Endpoint] = []

    @property
    def endpoints(self) -> list[Endpoint]:
        return self._endpoints

    def get_endpoints(self, access_points: set = None) -> dict[str, Endpoint]:
        """
        Get endpoints filtered by access point names.
        
        :param access_points: Set of endpoint names to filter by. If None, returns all endpoints.
        :return: Dictionary mapping endpoint names to Endpoint objects
        """
        if access_points is None:
            return {endpoint.name: endpoint for endpoint in self._endpoints}
        
        return {
            endpoint.name: endpoint 
            for endpoint in self._endpoints 
            if endpoint.name in access_points
        }

    @endpoints.setter
    def endpoints(self, endpoints: Union[Endpoint, list[Endpoint]]):
        if isinstance(endpoints, Endpoint):
            self.endpoints.append(endpoints)
        elif isinstance(endpoints, list):
            self.endpoints.extend(endpoints)
        else:
            raise TypeError("Expected Endpoint or list of Endpoints")

    @endpoints.deleter
    def endpoints(self):
        for endpoint in self.endpoints:
            # Close the agent including the connections
            endpoint.close()

        self._endpoints.clear()

    @abstractmethod
    def save_configuration(self) -> bool:
        pass

    @abstractmethod
    def delete_configuration(self, endpoint: Endpoint) -> bool:
        pass

    def get_endpoints_by_uuid(self, uuids: list[UUID]) -> list[Endpoint]:
        """
        Get endpoints by UUID.

        :param uuids: UUID or list of UUIDs to search for.
        :return: List of matching endpoints.
        """
        if isinstance(uuids, UUID):
            uuids = [uuids]

        matching_endpoints = [
            endpoint for endpoint in self.endpoints if endpoint.uuid in uuids
        ]

        return matching_endpoints

    def get_endpoint_uuid(self, endpoint_name: str) -> UUID:
        """
        Get the UUID of an endpoint by its name.

        :param endpoint_name: The name of the endpoint.
        :return: The UUID of the endpoint.
        """
        for endpoint in self.endpoints:
            if endpoint.name == endpoint_name:
                return endpoint.uuid

        raise ValueError(f"Endpoint with name '{endpoint_name}' not found.")

    def get_endpoint_by_uuid(self, uuid: UUID) -> Endpoint:
        """
        Get the endpoint by its UUID.

        :param uuid: The UUID of the endpoint.
        :return: The Endpoint object.
        """
        for endpoint in self.endpoints:
            if endpoint.uuid == uuid:
                return endpoint

        raise ValueError(f"Endpoint with UUID '{uuid}' not found.")

    def delete_endpoint(self, endpoint: Endpoint):
        """
        Delete an endpoint from the list and remove its configuration file.

        :param endpoint: The Endpoint object to delete.
        """
        if endpoint in self.endpoints:
            self.endpoints.remove(endpoint)
            self.delete_configuration(endpoint)
        else:
            raise KeyError(f"Endpoint {endpoint.uuid} not found.")
