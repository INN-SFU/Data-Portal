import json
import os
import dotenv

from uvicorn.config import LOGGING_CONFIG
from casbin.util.log import DEFAULT_LOGGING
from uuid import uuid5, NAMESPACE_DNS

from src.core.data_access_manager import DataAccessManager
from src.core.connectivity.agents import ArbutusAgent

# Reset the database and initialize secrets
CLEAN_AND_INITIALIZE = False
if CLEAN_AND_INITIALIZE:
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


# Make uvicorn and casbin loggers use the same format
# uvicorn logger
LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s [%(name)s]\t%(levelprefix)s\t%(message)s"
LOGGING_CONFIG["formatters"]["access"]["fmt"] = ('%(asctime)s [%(name)s]\t%(levelprefix)s\t%(client_addr)s - "%('
                                                 'request_line)s" %(status_code)s')
# casbin logger
DEFAULT_LOGGING["formatters"]["casbin_formatter"]["format"] = "{asctime} [{name}]\t{levelname}:\t\t{message}"

# Initialize DataAccessManager
dam = DataAccessManager()

# Initialize Data Access Point Agents
agents = [ArbutusAgent()]
