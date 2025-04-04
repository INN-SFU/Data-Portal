from abc import ABC, abstractmethod
from uuid import UUID


class AbstractUserManager(ABC):
    @abstractmethod
    def create_user(self, user_details: dict):
        pass

    @abstractmethod
    def get_user(self, uuid: UUID) -> dict:
        pass

    @abstractmethod
    def delete_user(self, uuid:UUID):
        pass

    @abstractmethod
    def get_all_users(self) -> list:
        pass

    @abstractmethod
    def user_exists(self, user_slug: str) -> bool:
        pass

    @abstractmethod
    def get_user_slug(self, uuid: UUID) -> str:
        pass

    @abstractmethod
    def get_user_uid(self, user_slug: str) -> UUID:
        pass

    @abstractmethod
    def get_user_uids(self) -> list:
        pass
