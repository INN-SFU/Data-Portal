import os
import logging

from .keycloak import KeycloakUserManager

logger = logging.getLogger('user-manager')

user_manager = KeycloakUserManager(realm_name=os.getenv("KEYCLOAK_REALM"),
                                   client_id=os.getenv("KEYCLOAK_ADMIN_CLIENT_ID"),
                                   client_secret=os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET"),
                                   base_url=os.getenv("KEYCLOAK_DOMAIN"))
