import os
import json

from uuid import UUID
from casbin import Enforcer


class DataAccessManager:
    def __init__(self):
        self.enforcer = Enforcer(os.getenv('ENFORCER_MODEL'), os.getenv('ENFORCER_ADAPTER'))
        self.user_policies_folder = os.getenv('USER_POLICIES')

        # Load uuids
        with open(os.getenv('UUID_STORE')) as f:
            self.uuids = json.load(f)

        # Load all user policies to enforcer

    def _load_user_policies(self):
        for uuid in self.uuids:
            with open(os.path.join(self.user_policies_folder, uuid + '.policies')) as f:
                for line in f:
                    self.enforcer.add_policy(*line.strip().split(", "))
            f.close()

    def _write_user_policies(self, uid_slug: str, uuid: UUID):
        user_policy_file = os.path.join(self.user_policies_folder, uuid.__str__() + '.policies')
        with open(user_policy_file, 'w') as f:
            for policy in self.enforcer.get_filtered_policy(0, uid_slug):
                f.write(f"p, {', '.join(policy)}\n")
        f.close()

    def _write_user_policy(self, uid_slug: str, resource: str, action: str):
        user_policy_file = os.path.join(self.user_policies_folder, self.uuids.get(uid_slug) + '.policies')
        with open(user_policy_file, 'a') as f:
            f.write(f"p, {uid_slug}, {resource}, {action}\n")
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

    def get_user_assets(self, uid_slug: str):
        return self.enforcer.get_permissions_for_user(uid_slug)

    def add_user_policy(self, uid_slug: str, resource: str, action: str):
        result = self.enforcer.add_policy(uid_slug, resource, action)
        if result:
            self._write_user_policy(uid_slug, resource, action)

    def remove_user_policies(self, uid_slug: str):
        result = self.enforcer.remove_filtered_policy(0, uid_slug)
        if result:
            user_policy_file = os.path.join(self.user_policies_folder, self.uuids.get(uid_slug) + '.policies')
            os.remove(user_policy_file)

    def add_user(self, uid_slug: str, uuid: UUID):
        self.uuids[uid_slug] = uuid.__str__()
        with open(os.getenv('UUID_STORE'), 'w') as f:
            json.dump(self.uuids, f, indent=4)
        f.close()


if __name__ == "__main__":
    import string
    import random
    import dotenv
    import uuid as uuid_
    from uuid import uuid5

    dotenv.load_dotenv("/Users/pmahon/Research/INN/Data Portal/DAM/src/api/.testenv")

    # Load DataAccessManager
    dam = DataAccessManager()

    for i in range(3):
        # Generate some new random user
        new_user = ''.join(random.choices(string.ascii_lowercase, k=5))
        user_uuid = uuid5(uuid_.NAMESPACE_OID, new_user)

        # Add the new user to the uuid store
        dam.add_user(new_user, user_uuid)

        print("Adding new user policy: ", new_user + ', ' + user_uuid.__str__())
        dam.add_user_policy(new_user, "data", "read")

        print("Updated Policies: ")
        print(dam.enforcer.get_policy())
