import json
import os
import shutil
from uuid import uuid5, NAMESPACE_DNS

from core.authentication.keycloak_utils import keycloak_administrator
from core.data_access_manager import DataAccessManager
from core.settings.security._generate_secrets import _generate_secrets


def create_admin_in_keycloak(admin_uid: str, password: str):
    user_representation = {
        "username": admin_uid,
        "email": admin_uid,
        "enabled": True,
        "credentials": [{"value": password, "temporary": False}]
    }
    user_id = keycloak_administrator.create_user(user_representation)
    return user_id


def SYS_RESET():
    print("WARNING: This will reset the database and initialize the service secrets.\n All existing user and admin data"
          "and _credentials will be lost.\n Do you want to continue? (y/n)")
    response = input().lower()
    if response != 'y':
        print('Exiting...')
        exit()

    dam = DataAccessManager()

    if dam.get_all_users() is not None:
        print('Removing existing users and associated data...')
        for user in dam.get_all_users():
            dam.remove_user(user)

    with open(os.getenv('UUID_STORE'), 'w') as file:
        json.dump({}, file)
    file.close()

    print('Removing logs...')
    for filename in os.listdir(os.getenv('LOG_FOLDER')):
        file_path = os.path.join(os.getenv('LOG_FOLDER'), filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to clear logs.')
            print('Failed to delete %s. Reason: %s' % (file_path, e))

    _generate_secrets()

    print('Initialize admin user...')

    print('Enter admin user ID:')
    admin_uid = input()
    print('Enter admin user password:')
    admin_key = input()
    create_admin_in_keycloak(admin_uid, admin_key)

    dam.add_user(admin_uid, uuid5(NAMESPACE_DNS, admin_key), 'admin')
    print(f'Admin User ID:\t{admin_uid}\nAdmin Key:\t{admin_key}')
    print('Admin user initialized successfully.')
    print("System reset complete.")
