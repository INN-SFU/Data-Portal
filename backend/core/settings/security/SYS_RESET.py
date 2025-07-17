import json
import os
import shutil

from core.settings.managers.users.keycloak.KeycloakUserManager import KeycloakUserManager
from core.management.users.models import UserCreate
from core.management.policies import DataAccessManager
from core.settings.security._generate_secrets import _generate_secrets


def SYS_RESET():
    print("WARNING: This will reset the database and initialize the service secrets.\n All existing user and admin data"
          "and _credentials will be lost.\n Do you want to continue? (y/n)")
    response = input().lower()
    if response != 'y':
        print('Exiting...')
        exit()

    print('Removing all users...')
    with open(os.getenv('UUID_STORE'), 'w') as file:
        json.dump({}, file)
    file.close()

    dam = DataAccessManager()

    # Initialize Keycloak admin client
    keycloak_administrator = KeycloakUserManager(
        realm_name=os.getenv('KEYCLOAK_REALM'),
        client_id=os.getenv('KEYCLOAK_ADMIN_CLIENT_ID'),
        client_secret=os.getenv('KEYCLOAK_ADMIN_CLIENT_SECRET'),
        base_url=os.getenv('KEYCLOAK_DOMAIN')
    )

    users = keycloak_administrator.get_all_users()

    for user in users:
        keycloak_administrator.delete_user(user.uuid)

        try:
            dam.remove_user(user.username)
        except ValueError:
            pass

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

    print('Removing all storage endpoints...')
    for endpoint_file in os.listdir(os.getenv('ENDPOINT_CONFIGS')):
        os.remove(os.path.join(os.getenv('ENDPOINT_CONFIGS'), endpoint_file))


    _generate_secrets()

    print('Initialize admin user...')

    print('Enter admin email:')
    admin_email = input()
    admin_username = admin_email.split('@')[0]
    print('Enter admin user password:')
    admin_key = input()
    
    # Create admin user using UserCreate model
    admin_user_create = UserCreate(
        username=admin_username,
        email=admin_email,
        roles=["admin"]
    )
    
    admin_user = keycloak_administrator.create_user(admin_user_create)
    
    dam.add_user(admin_username, admin_user.uuid, 'admin')

    # Provide the admin user with read and write access to all endpoints


    print('Admin user initialized successfully.')
    print("System reset complete.")
