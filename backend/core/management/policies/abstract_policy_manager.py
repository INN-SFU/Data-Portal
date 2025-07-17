from abc import ABC, abstractmethod
from uuid import UUID

from core.management.policies.models import Policy, Agreement
from core.management.users import AbstractUserManager


class AbstractPolicyManager(ABC):

    @property
    @abstractmethod
    def actions(self) -> list:
        raise NotImplementedError

    @abstractmethod
    def get_user_policies(self, user_uuid: UUID):
        raise NotImplementedError

    @abstractmethod
    def get_endpoint_policies(self, endpoint_uuid: UUID):
        raise NotImplementedError

    @abstractmethod
    def get_resource_policies(self, resource: str):
        raise NotImplementedError

    @abstractmethod
    def get_action_policies(self, action: str):
        raise NotImplementedError

    @abstractmethod
    def filter_policies(self,
                        filter_: Policy) -> dict:
        """
        Get all policies according to the given filters.

        :param filter_: The filter to be applied.
        """
        raise NotImplementedError

    def add_policies(self, policies: list[Policy]) -> bool:
        """
        Add a new policy or a list of policies.

        :param policies: The policy or list of policies to be added.
        :return: True if all added successfully, False otherwise.
        """
        for policy in policies:
            if not self.add_policy(policy):
                return False
        return True

    @abstractmethod
    def add_policy(self, policy: Policy) -> bool:
        """
        Add a new policy.

        :param policy: The policy to be added.
        :return: True if successful, False otherwise.
        """
        raise NotImplementedError

    def remove_policies(self, policies: list[Policy]) -> bool:
        """
        Remove a policy or a list of policies.
        :param policies: The policy or list of policies to be removed.
        :return: True if all removed successfully, False otherwise.
        """
        for policy in policies:
            if not self.remove_policy(policy):
                return False
        return True

    @abstractmethod
    def remove_policy(self, policy: Policy) -> bool:
        """
        Remove a policy.

        :param policy: The policy to be removed.
        :type policy: Policy
        :return: True if successful, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def create_user_policy_store(self, user_uuid: UUID) -> bool:
        """
        Create a user policy store for the given UUID.

        :param user_uuid: The UUID of the user.
        :return: True if successful, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def remove_user_policy_store(self, user_uuid: UUID) -> bool:
        """
        Remove the user policy store for the given UUID.

        :param user_uuid: The UUID of the user.
        :return: True if successful, False otherwise.
        """
        raise NotImplementedError

    def validate_policies(self, policies: list[Policy]) -> bool:
        """
        Validate the given policies.

        :param policies: The policies to be validated.
        :return: True if all policies valid, False otherwise.
        """
        for policy in policies:
            if not self.validate_policy(policy):
                return False
        return True

    @abstractmethod
    def validate_policy(self, policy: Policy) -> bool:
        """
        Validate a single policy.

        :param policy: The policy to be validated.
        :return: True if valid, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def create_agreement(self, agreement: Agreement) -> bool:
        """
        Create a new agreement.

        :param agreement: The agreement to be created.
        :type agreement: Agreement
        :return: True if successful, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def remove_agreement(self, agreement: Agreement) -> bool:
        """
        Remove the agreement with the given UID.

        :param agreement: The agreement to be removed.
        :type agreement: Agreement
        :return: True if successful, False otherwise.
        """
        raise NotImplementedError
