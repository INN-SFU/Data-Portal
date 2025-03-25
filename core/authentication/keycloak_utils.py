import os
import requests
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from keycloak.keycloak_admin import KeycloakAdmin

# Initialize the Keycloak Admin client using admin credentials (store these securely)
keycloak_administrator = KeycloakAdmin(
    server_url=os.getenv("KEYCLOAK_DOMAIN") + "/",
    username=os.getenv("KEYCLOAK_ADMIN_USERNAME"),  # e.g. "admin"
    password=os.getenv("KEYCLOAK_ADMIN_PASSWORD"),  # e.g. "admin"
    realm_name=os.getenv("KEYCLOAK_REALM"),
    verify=True
)

# Use HTTPBearer to extract the token from the Authorization header.
bearer_scheme = HTTPBearer()


def get_jwks_client():
    """
    Creates a PyJWKClient using the JWKS URI from Keycloak's well-known configuration.
    """
    well_known_url = os.getenv("KEYCLOAK_WELL_KNOWN_URL")
    if not well_known_url:
        raise Exception("KEYCLOAK_WELL_KNOWN_URL is not set")
    oidc_config = requests.get(well_known_url).json()
    jwks_uri = oidc_config.get("jwks_uri")
    if not jwks_uri:
        raise Exception("jwks_uri not found in OIDC configuration")
    return PyJWKClient(jwks_uri)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """
    Validates the JWT token issued by Keycloak and returns its payload.
    """
    token = credentials.credentials
    client_id = os.getenv("KEYCLOAK_CLIENT_ID")
    keycloak_domain = os.getenv("KEYCLOAK_DOMAIN")
    realm = os.getenv("KEYCLOAK_REALM")

    if not (client_id and keycloak_domain and realm):
        raise Exception("Keycloak configuration environment variables are not set properly")

    issuer = f"{keycloak_domain}/realms/{realm}"
    jwks_client = get_jwks_client()

    try:
        # Retrieve the signing key that matches the token's "kid"
        signing_key = jwks_client.get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=issuer
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        ) from e
    return payload


def is_user_admin(token_payload: dict) -> bool:
    """
    Checks if the token payload indicates that the user has admin privileges.
    """
    roles = token_payload.get("realm_access", {}).get("roles", [])
    return "admin" in roles


def create_user(username: str, email: str, first_name: str, last_name: str, password: str):
    user_representation = {
        "username": username,
        "email": email,
        "enabled": True,
        "firstName": first_name,
        "lastName": last_name,
        "credentials": [{"value": password, "temporary": False}]
    }
    user_id = keycloak_admin.create_user(user_representation)
    return user_id


def delete_user(username: str):
    # Find the user by username
    users = keycloak_admin.get_users(query={"username": username})
    if not users:
        raise ValueError("User not found")
    user_id = users[0]["id"]
    keycloak_admin.delete_user(user_id)