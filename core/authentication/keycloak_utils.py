import os

import requests
from keycloak.connection import ConnectionManager
from keycloak.keycloak_admin import KeycloakAdmin

# Initialize the Keycloak Admin clients:
# For administrative operations:
data = {
    "grant_type": "client_credentials",
    "client_id": "ams-admin-cli",
    "client_secret": os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET")
}
resp = requests.post(
    "http://localhost:8080/realms/INN-AMS/protocol/openid-connect/token",
    data=data
)
token_json = resp.json()
access_token = token_json["access_token"]

# 1) Set the base_url to just http://localhost:8080
connection = ConnectionManager(
    base_url="http://localhost:8080",  # no /admin or realm in the URL
    headers={"Authorization": f"Bearer {access_token}"}
)

# 2) Manually set the realm_name so the library can build correct paths
connection.realm_name = "INN-AMS"

# 3) Initialize KeycloakAdmin with that connection
keycloak_administrator = KeycloakAdmin(connection=connection)

# For the UI client (if needed elsewhere):
keycloak_ui_cli = KeycloakAdmin(
    server_url=os.getenv("KEYCLOAK_DOMAIN") + "/",
    client_id=os.getenv("KEYCLOAK_UI_CLIENT_ID"),
    client_secret_key=os.getenv("KEYCLOAK_UI_CLIENT_SECRET"),
    realm_name=os.getenv("KEYCLOAK_REALM"),
    verify=True
)


def create_user(username: str, email: str, password: str,  first_name: str = None, last_name: str = None ,roles: list[str] = None):
    """
    Creates a user using the administrative service account.
    """
    user_representation = {
        "username": username,
        "email": email,
        "enabled": True,
        "firstName": first_name,
        "lastName": last_name,
        "credentials": [{"value": password, "temporary": False}]
    }
    user_id = keycloak_administrator.create_user(user_representation)

    # Step 2: assign roles
    for role in roles:
        keycloak_administrator.assign_realm_roles(
            user_id=user_id,
            roles=[{"name": role}]
        )
    return user_id


def delete_user(username: str):
    """
    Deletes a user using the administrative service account.
    """
    # Find the user by username
    users = keycloak_administrator.get_users(query={"username": username})
    if not users:
        raise ValueError("User not found")
    user_id = users[0]["id"]
    keycloak_administrator.delete_user(user_id)
