import json
import os
import shutil
from uuid import uuid5, NAMESPACE_DNS

from ..data_access_manager import DataAccessManager
from ._generate_secrets import _generate_secrets
from core.authentication.auth import generate_credentials


def SYS_RESET():
    print("WARNING: This will reset the database and initialize the service secrets.\n All existing user and admin data "
          "and credentials will be lost.\n Do you want to continue? (y/n)")
    response = input().lower()
    if response != 'y':
        print('Exiting...')
        exit()

    dam = DataAccessManager()

    if dam.get_users() is not None:
        print('Removing existing users and associated data...')
        for user in dam.get_users():
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
    _, admin_key = generate_credentials(admin_uid)

    dam.add_user(admin_uid, uuid5(NAMESPACE_DNS, admin_key), 'admin')
    print(f'Admin User ID:\t{admin_uid}\nAdmin Key:\t{admin_key}')
