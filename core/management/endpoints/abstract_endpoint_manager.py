from typing import Iterable, Union
from uuid import UUID
from abc import abstractmethod, ABC

from core.connectivity import AbstractStorageAgent


class AbstractEndpointManager(ABC):

    @property
    @abstractmethod
    def endpoints(self) -> dict[UUID, AbstractStorageAgent]:
        pass

    @abstractmethod
    def get_endpoints(self) -> dict[UUID, AbstractStorageAgent]:
        pass

    @abstractmethod
    def add_endpoint(self, value: dict[UUID, AbstractStorageAgent]):
        pass

    @abstractmethod
    def get_endpoint(self, uid: Union[UUID, Iterable[UUID]]) -> AbstractStorageAgent:
        pass

    @abstractmethod
    def delete_endpoint(self, uid: UUID):
        pass

    @abstractmethod
    def get_slug(self, uid: UUID) -> str:
        pass

    @abstractmethod
    def get_uid(self, endpoint_slug: str) -> UUID:
        pass

    @abstractmethod
    def get_administrator(self, uuid: UUID) -> str:
        pass
