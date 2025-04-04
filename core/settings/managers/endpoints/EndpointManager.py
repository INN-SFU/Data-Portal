import logging
from typing import Union, Iterable, Dict
from uuid import UUID

from core.connectivity.abstract_storage_agent import AbstractStorageAgent
from core.management.endpoints.abstract_endpoint_manager import AbstractEndpointManager

logger = logging.getLogger("app")


class EndpointManager(AbstractEndpointManager):

    def __init__(self):
        self._endpoints = {}

    @property
    def endpoints(self) -> dict[UUID, AbstractStorageAgent]:
        return self._endpoints

    def get_endpoints(self) -> dict[UUID, AbstractStorageAgent]:
        return self._endpoints

    def get_endpoint(self, uid: Union[UUID, Iterable[UUID]]) -> Union[AbstractStorageAgent, Dict[UUID, AbstractStorageAgent]]:
        if isinstance(uid, UUID):
            # Single UUID case: return a single endpoint.
            return self.endpoints.get(uid)
        elif isinstance(uid, Iterable):
            # Iterable case: build a dict mapping each UUID to its endpoint.
            return {u: self.endpoints.get(u) for u in uid}
        else:
            raise TypeError("uid must be a UUID or an iterable of UUIDs.")

    def add_endpoint(self, value: dict[UUID, AbstractStorageAgent]):
        self.endpoints.update(value)

    def delete_endpoint(self, uid: UUID):
        del self.endpoints[uid]

    def get_slug(self, uid: UUID) -> str:
        return self.get_endpoint(uid).access_point_slug

    def get_uid(self, endpoint_slug: str) -> UUID:
        for uid, endpoint in self.endpoints.items():
            if endpoint.access_point_slug == endpoint_slug:
                return uid

    def get_administrator(self, uuid: UUID) -> str:
        pass
