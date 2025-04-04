from abc import ABC, abstractmethod, abstractproperty
from uuid import UUID


class AbstractPolicyManager(ABC):

    @property
    @abstractmethod
    def actions(self) -> list:
        raise NotImplementedError

    @abstractmethod
    def get_user_policies(self, uuid: UUID):
        raise NotImplementedError

    @abstractmethod
    def get_access_point_policies(self, access_point_uid: UUID):
        raise NotImplementedError

    @abstractmethod
    def get_resource_policies(self, resource: str):
        raise NotImplementedError

    @abstractmethod
    def get_action_policies(self, action: str):
        raise NotImplementedError

    @abstractmethod
    def filter_policies(self, uuid: UUID, access_point_uid: UUID = None, action: str = None) -> dict:
        raise NotImplementedError

    @abstractmethod
    def add_policy(self, uuid: UUID, access_point_uid: UUID, resource: str, action: str):
        raise NotImplementedError

    def remove_policy(self, uuid: UUID, access_point_uid: UUID, resource: str, action: str):
        raise NotImplementedError

    @abstractmethod
    def create_user_policy_store(self, uuid: UUID):
        raise NotImplementedError

    @abstractmethod
    def remove_user_policy_store(self, uuid: UUID):
        raise NotImplementedError

    @abstractmethod
    def validate_policy(self, uuid: UUID, access_point_uid: UUID, resource: str, action: str):
        raise NotImplementedError

    def get_policy(self, uuid: UUID, access_point_uid: UUID, resource: str, action: str):
        raise NotImplementedError
