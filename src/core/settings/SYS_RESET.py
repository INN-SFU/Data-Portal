import json
import os
from uuid import uuid5, NAMESPACE_DNS

from ..data_access_manager import DataAccessManager


def SYS_RESET():
    print("WARNING: This will reset the database and initialize the server secrets.\n All existing user and admin data "
          "and credentials will be lost.\n Do you want to continue? (y/n)")
    response = input().lower()
    if response != 'y':
        print('Exiting...')
        exit()

    from ._generate_secrets import _generate_secrets
    from src.core.authentication.auth import generate_credentials
    print('Cleaning...')
    users_policies = os.listdir(os.getenv('USER_POLICIES'))
    for policy in users_policies:
        file = os.path.join(os.getenv('USER_POLICIES'), policy)
        os.remove(file)

    with open(os.getenv('UUID_STORE'), 'w') as file:
        json.dump({}, file)
    file.close()

    _generate_secrets()

    print('Initialize admin user...')

    print('Enter admin user ID:')
    admin_uid = input()
    _, admin_key = generate_credentials(admin_uid)

    dam = DataAccessManager()
    dam.add_user(admin_uid, uuid5(NAMESPACE_DNS, admin_key), 'admin')
    print(f'Admin User ID:\t{admin_uid}\nAdmin Key:\t\t{admin_key}')
