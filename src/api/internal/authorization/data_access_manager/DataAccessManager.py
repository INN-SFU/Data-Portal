"""
Author: Patrick Mahon
Date: 2021-09-30
Email: pmahon@sfu.ca
"""
import os
import json

from uuid import UUID
from casbin import Enforcer


class DataAccessManager:
    """
    DataAccessManager:

    Class that provides methods for managing user policies and permissions.

    Attributes:
        enforcer (Enforcer): An instance of the Enforcer class for enforcing access control policies.
        user_policies_folder (str): The path to the folder where user policies are stored.
        uuids (dict): A dictionary containing user UUIDs mapped to their unique identifiers.

    Methods:
        __init__():
            Constructor method that initializes the DataAccessManager object.

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

    def __init__(self):
        self.enforcer = Enforcer(os.getenv('ENFORCER_MODEL'), None, enable_log=True)
        self.user_policies_folder = os.getenv('USER_POLICIES')

        # Load uuids
        with open(os.getenv('UUID_STORE')) as f:
            self.uuids = json.load(f)

        # Load all user policies to enforcer
        self._load_user_policies()

    def _load_user_policies(self):
        """
        Load user policies from files.

        :return: None
        """
        for uid in self.uuids.keys():
            with open(os.path.join(self.user_policies_folder, self.uuids[uid]['uuid'] + '.policies')) as f:
                for line in f:
                    self.enforcer.add_policy(*line.strip().split(", ")[1:])
            f.close()

    def _write_user_policies(self, uid_slug: str, uuid: UUID):
        """
        Write user policies to a file.

        :param uid_slug: The slug of the user's UID.
        :param uuid: The UUID of the user.
        :return: None
        """
        user_policy_file = os.path.join(self.user_policies_folder, uuid.__str__() + '.policies')
        with open(user_policy_file, 'w') as f:
            for policy in self.enforcer.get_filtered_policy(0, uid_slug):
                f.write(f"p, {', '.join(policy)}\n")
        f.close()

    def _write_user_policy(self, uid_slug: str, access_point_slug: str, resource: str, action: str):
        """
        Write a user policy to a file.

        :param uid_slug: The unique identifier slug of the user.
        :param resource: The resource the user wants to access.
        :param action: The action the user wants to perform on the resource.
        :return: None
        """
        user_policy_file = os.path.join(self.user_policies_folder, self.uuids.get(uid_slug)['uuid'] + '.policies')
        with open(user_policy_file, 'a') as f:
            f.write(f"p, {uid_slug}, {access_point_slug}, {resource}, {action}\n")
        f.close()

    def _write_enforcer_policies(self, enforcer: Enforcer):
        """
        Write the policies of an enforcer object to a csv file.

        NOTE: This will overwrite the existing csv file.

        :param enforcer: The enforcer object containing the policies.
        :type enforcer: Enforcer
        """
        for uid_slug in enforcer.get_all_named_subjects("p"):
            # Retrieve the uuid from the uuid store
            uuid = self.uuids.get(uid_slug)
            self._write_user_policies(uid_slug, uuid)

    def get_policy(self, uid_slug: str, access_point_slug: str, resource: str, action: str):
        """
        Get the filtered policy based on the provided parameters.

        :param uid_slug: User ID or user slug.
        :type uid_slug: str

        :param access_point_slug: Access point identifier or access point slug.
        :type access_point_slug: str

        :param resource: Resource identifier or resource slug.
        :type resource: str

        :param action: Action identifier or action slug.
        :type action: str

        :return: Filtered policy matching the provided parameters.
        :rtype: list

        """
        return self.enforcer.get_filtered_policy({'p': [uid_slug, access_point_slug, resource, action]})

    def add_user_policy(self, uid_slug: str, access_point_slug: str, resource: str, action: str):
        """
        Adds a user policy to the system.

        :param uid_slug: The slug of the user identifier.
        :type uid_slug: str
        :param access_point_slug: The slug of the access point.
        :type access_point_slug: str
        :param resource: The resource to grant access to.
        :type resource: str
        :param action: The action to be performed on the resource.
        :type action: str
        :return: Returns True if the policy was successfully added.
        :rtype: bool
        :raises ValueError: If the policy already exists or failed to add the policy.
        """
        # Check if the policy already exists
        if self.enforcer.has_policy(uid_slug, resource, action):
            raise ValueError("Policy already exists.")

        result = self.enforcer.add_policy(uid_slug, access_point_slug, resource, action)
        if result:
            self._write_user_policy(uid_slug, access_point_slug, resource, action)
            return True
        else:
            raise ValueError("Failed to add policy.")

    def remove_policy(self, uid_slug: str, access_point_slug: str, resource: str, action: str):
        """
        Remove a policy from the enforcer.

        :param uid_slug: The UID slug associated with the policy.
        :param access_point_slug: The access point slug associated with the policy.
        :param resource: The resource associated with the policy.
        :param action: The action associated with the policy.
        :return: True if the policy was successfully removed.
        :raises ValueError: If the policy fails to be removed.
        """
        result = self.enforcer.remove_filtered_policy({'p': [uid_slug, access_point_slug, resource, action]})
        if result:
            self._write_user_policies(uid_slug, self.uuids.get(uid_slug)['uuid'])
            return True
        else:
            raise ValueError("Failed to remove policy.")

    def add_user(self, uid_slug: str, uuid: UUID, role: str):
        """

        This method adds a user to the system.

        :param uid_slug: A string representing a unique identifier for the user.
        :param uuid: A UUID object representing a unique identifier for the user.
        :param role: A string representing the role of the user.
        :return: True if the user is successfully added, otherwise raises a ValueError if the user already exists.
        """
        if self.uuids.get(uid_slug):
            raise ValueError("User already exists.")

        # Create a new user policy file
        user_policy_file = os.path.join(self.user_policies_folder, uuid.__str__() + '.policies')
        with open(user_policy_file, 'w') as f:
            f.write("")
        f.close()

        # Add the user to the uuid store
        self.uuids[uid_slug] = {"uuid": uuid.__str__(), "role": role}

        # Write the updated uuid store to disk
        with open(os.getenv('UUID_STORE'), 'w') as f:
            json.dump(self.uuids, f, indent=4)
        f.close()

        return True

    def remove_user(self, uid_slug: str):
        """
        Remove User

        Removes a user from the system based on a unique identifier.

        :param uid_slug: The unique identifier of the user to remove.
        :type uid_slug: str
        """
        if self.uuids.get(uid_slug) is None:
            raise ValueError("User does not exist.")

        # Delete the user policies
        user_policy_file = os.path.join(self.user_policies_folder, self.uuids.get(uid_slug)['uuid'] + '.policies')
        try:
            os.remove(user_policy_file)
        except FileNotFoundError:
            pass

        # Remove user policies from enforcer
        self.enforcer.remove_filtered_policy(0, uid_slug)

        # Remove the user from the uuid store
        del self.uuids[uid_slug]

        # Write the updated uuid store to disk
        with open(os.getenv('UUID_STORE'), 'w') as f:
            json.dump(self.uuids, f, indent=4)
        f.close()

        return True

    def get_user(self, uid: str):
        """
        Get user information based on the provided UID.

        :param uid: The unique identifier of the user.
        :type uid: str
        :return: A dictionary containing user information including UID, UUID, role, and policies.
                 Returns None if the user with the given UID is not found.
        :rtype: dict or None
        """
        if self.uuids.get(uid) is None:
            return None

        uuid = self.uuids.get(uid).get("uuid")
        role = self.uuids.get(uid).get("role")
        policies = self.enforcer.get_filtered_policy(0, uid)

        return {"uid": uid, "uuid": uuid, "role": role, "policies": policies}

    def get_users(self):
        """
        Returns a list of all users.

        :return: A list of all users.
        :rtype: list
        """
        return list(self.uuids.keys())

    def validate_user_access(self, uid_slug: str, access_point_slug: str, resource: str, action: str):
        """
        Validate user access based on the provided parameters.

        :param uid_slug: The unique identifier of the user.
        :param access_point_slug: The unique identifier of the access point.
        :param resource: The resource to be accessed.
        :param action: The action to be performed on the resource.
        :return: True if the user has access, False otherwise.
        """
        return self.enforcer.enforce(uid_slug, access_point_slug, resource, action)


if __name__ == "__main__":
    import string
    import random
    import dotenv
    import uuid as uuid_
    from uuid import uuid5
    import os

    dotenv.load_dotenv("/Users/pmahon/Research/INN/Data Portal/DAM/src/api/config/.env")

    # Load DataAccessManager
    dam = DataAccessManager()

    # for i in range(3):
    #    # Generate some new random user
    #    new_user = ''.join(random.choices(string.ascii_lowercase, k=5))
    #    user_uuid = uuid5(uuid_.NAMESPACE_OID, new_user)
    #    role = "user"
    #
    #    # Add the new user to the uuid store
    #    dam.add_user(new_user, user_uuid, role)
    #
    #    print("Adding new user policy: ", new_user + ', ' + user_uuid.__str__())
    #    dam.add_user_policy(new_user, "data", "read")

    new_user = 'pmahon@sfu.ca'
    user_uuid = uuid5(uuid_.NAMESPACE_OID, new_user)
    role_ = "admin"

    # Add the new user to the uuid store
    dam.add_user(new_user, user_uuid, role_)
