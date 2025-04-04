"""
Author: Patrick Mahon
Date: 2021-09-30
Email: pmahon@sfu.ca
"""
import os
from abc import ABC

from uuid import UUID
from casbin import Enforcer
from core.management.policies.abstract_policy_manager import AbstractPolicyManager


class CasbinPolicyManager(AbstractPolicyManager):
    """
    PolicyManager:

    Class that provides methods for managing user policies and permissions.

    Attributes:
        enforcer (Enforcer): An instance of the Enforcer class for enforcing access control policies.
        user_policies_folder (str): The path to the folder where user policies are stored.
        uuids (dict): A dictionary containing user UUIDs mapped to their unique identifiers.

    Methods:
        __init__():
            Constructor method that initializes the PolicyManager object.

        _load_user_policies():
            Loads all user policies from the user policies folder into the enforcer object.

        _write_user_policies(uid_slug: str, uuid: UUID):
            Writes the user policies for a given UID slug and UUID to a file.

        _write_user_policy(uid_slug: str, resource: str, action: str):
            Writes a single user policy for a given UID slug, resource, and action to a file.

        _write_enforcer_policies(enforcer: Enforcer):
            Writes all the policies of an enforcer object to a CSV file.

        get_user_assets(uid_slug: str):
            Returns the permissions for a specified user.

        add_user_policy(uid_slug: str, resource: str, action: str):
            Adds a new policy for a specified user, resource, and action.

        remove_policy(uid_slug: str, resource: str, action: str):
            Removes a policy for a specified user, resource, and action.

        add_user(uid_slug: str, uuid: UUID, role: str):
            Adds a new user with a unique identifier, UUID, and role.

        remove_user(uid_slug: str):
            Removes a user based on a unique identifier.

        get_user(uid: str):
            Returns information about a user based on a unique identifier.

        get_users():
            Returns a list of all user unique identifiers.

    """

    def __init__(self, uuids):

        """
        Load user policies from files.

        :return: None
        """

        self.enforcer = Enforcer(os.getenv('ENFORCER_MODEL'), os.getenv('ENFORCER_POLICY'), enable_log=True)
        self.user_policies_folder = os.getenv('USER_POLICIES')
        self._actions = ['read', 'write', 'share']

        # Load all user policies to enforcer
        for uuid in uuids:
            policy_file = os.path.join(self.user_policies_folder, uuid.__str__() + '.policies')
            with open(policy_file, 'r') as f:
                for line in f.readlines():
                    self.enforcer.add_policy(*line.strip().split(", ")[1:])
            f.close()

    @property
    def actions(self):
        return self.actions

    def _write_user_policies(self, uuid: UUID):
        """
        Write user policies to a file.
        """
        user_policy_file = os.path.join(self.user_policies_folder, uuid.__str__() + '.policies')
        with open(user_policy_file, 'w') as f:
            for policy in self.enforcer.get_filtered_policy(0, uuid):
                f.write(f"p, {', '.join(policy)}\n")
        f.close()

    def _write_user_policy(self, uuid: UUID, access_point_uid: UUID, resource: str, action: str):
        """
        Write a user policy to a file.

        :param uuid: The unique identifier slug of the user.
        :param resource: The resource the user wants to access.
        :param action: The action the user wants to perform on the resource.
        :return: None
        """
        # Retrieve the users policy file
        user_policy_file = os.path.join(self.user_policies_folder, uuid.__str__() + '.policies')
        # Write the policy
        with open(user_policy_file, 'a') as f:
            f.write(f"p, {uuid.__str__()}, {access_point_uid.__str__()}, {resource}, {action}\n")
        f.close()

    def _write_enforcer_policies(self, enforcer: Enforcer):
        """
        Write the policies of an enforcer object to a csv file.

        NOTE: This will overwrite the existing csv file.

        :param enforcer: The enforcer object containing the policies.
        :type enforcer: Enforcer
        """
        for uuid in enforcer.get_all_named_subjects("p"):
            self._write_user_policies(uuid)

    def get_user_policies(self, uuid: UUID):
        """
        Get the user policies.

        :return: The filtered user policies.
        :rtype: list[str]
        """
        return self.enforcer.get_filtered_policy(0, uuid.__str__())

    def get_access_point_policies(self, access_point_uid: UUID):
        """
        Get the access point policies.

        :return: The filtered access point policies.
        :rtype: list[str]
        """
        return self.enforcer.get_filtered_policy(1, access_point_uid.__str__())

    def get_resource_policies(self, resource: str):
        """
        Get the resource policies.

        :param resource: The resource to be accessed.
        :type resource: str
        :return: The filtered resource policies.
        :rtype: list[str]
        """
        return self.enforcer.get_filtered_policy(2, resource)

    def get_action_policies(self, action: str):
        """
        Get the action policies.

        :param action: The action to be performed on the resource.
        :type action: str
        :return: The filtered action policies.
        :rtype: list[str]
        """
        return self.enforcer.get_filtered_policy(3, action)

    def filter_policies(self, uuid: UUID, access_point_uid: UUID = None, action: str = None) -> dict:
        """
        Get all policies under a user according the given filters.


        """
        # If access point or action are None set to any access point of action
        if access_point_uid is None:
            access_point_uid = ""
        if action is None:
            action = ""

        filter_ = (uuid.__str__(), access_point_uid, '', action)

        # Retrieve the policies matching the filter
        policies = self.enforcer.get_filtered_policy(0, *filter_)

        # Sort by access points
        access_points = set([policy[1] for policy in policies])
        assets = dict.fromkeys(access_points, [])
        for policy in policies:
            assets[policy[1]].append(policy[2])
        return assets

    def add_policy(self, uuid: UUID, access_point_uid: UUID, resource: str, action: str):
        """
        Adds a user policy to the system.

        :param access_point_uid:
        :param uuid:
        :param resource: The resource to grant access to.
        :type resource: str
        :param action: The action to be performed on the resource.
        :type action: str
        :return: Returns True if the policy was successfully added.
        :rtype: bool
        :raises ValueError: If the policy already exists or failed to add the policy.
        """
        # Check if the policy already exists
        if self.enforcer.has_policy(uuid.__str__(), resource, action):
            raise ValueError("Policy already exists.")

        result = self.enforcer.add_policy(uuid.__str__(), access_point_uid.__str__(), resource, action)
        if result:
            self._write_user_policy(uuid, access_point_uid, resource, action)
            return True
        else:
            raise ValueError("Failed to add policy.")

    def remove_policy(self, uuid: UUID, access_point_uid: UUID, resource: str, action: str):
        """
        Remove a policy from the enforcer.

        :param uuid:
        :param access_point_uid:
        :param resource: The resource associated with the policy.
        :param action: The action associated with the policy.
        :return: True if the policy was successfully removed.
        :raises ValueError: If the policy fails to be removed.
        """
        filter_ = (uuid.__str__(), access_point_uid.__str__(), resource, action)
        result = self.enforcer.remove_filtered_policy(0, *filter_)
        if result:
            self._write_user_policies(uuid)
            return True
        else:
            raise ValueError("Failed to remove policy.")

    def create_user_policy_store(self, uuid: UUID):
        """
        Creates a policy file for the given unique user identifier.
        """

        # Create a new user policy file
        user_policy_file = os.path.join(self.user_policies_folder, uuid.__str__() + '.policies')

        # Check if the file exists
        if os.path.exists(user_policy_file):
            raise FileExistsError('The user policy file already exists.')

        with open(user_policy_file, 'w') as f:
            f.write("")
        f.close()

        return

    def remove_user_policy_store(self, uuid: UUID):
        """
        Removes a policy file for the given unique user identifier.
        """

        # Delete the user policies
        user_policy_file = os.path.join(self.user_policies_folder, uuid.__str__() + '.policies')
        try:
            os.remove(user_policy_file)
        except FileNotFoundError:
            return

        # Remove user policies from enforcer
        self.enforcer.remove_filtered_policy(0, uuid)

        return True

    def validate_policy(self, uuid: UUID, access_point_uid: UUID, resource: str, action: str):
        """
        Validate user access based on the provided parameters.

        :param uuid:
        :param access_point_uid:
        :param resource: The resource to be accessed.
        :param action: The action to be performed on the resource.
        :return: True if the user has access, False otherwise.
        """
        return self.enforcer.enforce(uuid, access_point_uid, resource, action)
