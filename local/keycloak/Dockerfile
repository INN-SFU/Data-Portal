FROM quay.io/keycloak/keycloak:24.0.3

# Copy realm export for auto-import
# Keycloak will automatically import this on startup with --import-realm flag
COPY keycloak-realm-export.json /opt/keycloak/data/import/realm.json

# Note: Additional Keycloak configuration (service accounts, scopes, roles)
# is handled by init_keycloak.sh which runs from the backend container
# after Keycloak is ready, since the base image lacks curl/python3
