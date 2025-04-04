import requests


from uuid import UUID

from keycloak.keycloak_admin import KeycloakAdmin
from keycloak.connection import ConnectionManager
from core.management.users import AbstractUserManager


class KeycloakUserManager(AbstractUserManager):

    def __init__(self, realm_name: str, client_id: str, client_secret: str, base_url: str, grant_type: str,
                 protocol: str = "openid-connect"):
        data = {
            "grant_type": grant_type,
            "client_id": client_id,
            "client_secret": client_secret
        }

        resp = requests.post(
            url=f"{base_url}/realms/{realm_name}/protocol/{protocol}/token",
            data=data
        )
        token_json = resp.json()
        access_token = token_json["access_token"]

        # 1) Set the base_url to just http://localhost:8080
        connection = ConnectionManager(
            base_url=base_url,  # no /admin or realm in the URL
            headers={"Authorization": f"Bearer {access_token}"}
        )

        # 2) Manually set the realm_name so the library can build correct paths
        connection.realm_name = realm_name

        # 3) Initialize KeycloakAdmin with that connection
        self.identity_manager = KeycloakAdmin(connection=connection)

    def create_user(self, user_details: dict):
        return self.identity_manager.create_user(user_details)

    def get_user(self, uuid: UUID) -> dict:
        return self.identity_manager.get_user(user_id=uuid.__str__())

    def delete_user(self, uuid: UUID):
        return self.identity_manager.delete_user(user_id=uuid.__str__())

    def get_all_users(self) -> list:
        return self.identity_manager.get_users()

    def user_exists(self, user_slug: str) -> bool:
        if self.identity_manager.get_user_id(username=user_slug) is not None:
            return True
        return False

    def get_user_slug(self, uuid: UUID) -> str:
        user = self.identity_manager.get_user(uuid.__str__())
        return user['preferred_username']

    def get_user_uid(self, user_slug: str) -> UUID:
        return UUID(self.identity_manager.get_user_id(username=user_slug))

    def get_user_uids(self) -> list:
        return [UUID(user['id']) for user in self.identity_manager.get_users()]
