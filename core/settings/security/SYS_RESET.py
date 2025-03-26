import json
import os
import shutil

from core.authentication.keycloak_utils import keycloak_administrator
from core.data_access_manager import DataAccessManager
from core.settings.security._generate_secrets import _generate_secrets


def SYS_RESET():
    print("WARNING: This will reset the database and initialize the service secrets.\n All existing user and admin data"
          "and _credentials will be lost.\n Do you want to continue? (y/n)")
    response = input().lower()
    if response != 'y':
        print('Exiting...')
        exit()

    dam = DataAccessManager()

    print('Removing all users...')
    users = keycloak_administrator.get_users()

    for user in users:
        keycloak_administrator.delete_user(user['id'])

        try:
            dam.remove_user(user['username'])
        except ValueError:
            pass

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

    print('Enter admin email:')
    admin_email = input()
    admin_username = admin_email.split('@')[0]
    print('Enter admin user password:')
    admin_key = input()
    user_representation = {
        "username": admin_username,
        "email": admin_email,
        "enabled": True,
        "credentials": [{"value": admin_key, "temporary": False}]
    }
    keycloak_administrator.create_user(user_representation)
    admin_id = keycloak_administrator.get_users(query={"username": admin_username})[0]['id']
    admin_role_obj = keycloak_administrator.get_realm_role("admin")
    keycloak_administrator.assign_realm_roles(
        user_id=admin_id,
        roles=[admin_role_obj]
    )

    dam.add_user(admin_username, admin_id, 'admin')
    print('Admin user initialized successfully.')
    print("System reset complete.")
