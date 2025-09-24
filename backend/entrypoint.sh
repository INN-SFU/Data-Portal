#!/bin/bash
set -e

# Defaults for logging
export LOG_DIR="${LOG_DIR:-/app/data/logs}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Generate config.yaml from environment variables
cat > "${APP_DIR:-/app}/config.yaml" <<EOL
system:
  reset: ${SYSTEM_RESET:-false}

uvicorn:
  host: ${AMS_HOST:-0.0.0.0}
  port: ${AMS_PORT:-${APP_PORT:-8000}}
  reload: ${AMS_RELOAD:-false}

keycloak:
  domain: ${KEYCLOAK_DOMAIN}
  realm: ${KEYCLOAK_REALM:-ams-portal}
  ui_client_id: ${KEYCLOAK_UI_CLIENT_ID:-ams-portal-ui}
  ui_client_secret: ${KEYCLOAK_UI_CLIENT_SECRET:-}
  admin_client_id: ${KEYCLOAK_ADMIN_CLIENT_ID:-ams-portal-admin}
  admin_client_secret: ${KEYCLOAK_ADMIN_CLIENT_SECRET}
  redirect_uri: ${KEYCLOAK_REDIRECT_URI}

logging:
  config: ${LOG_CONFIG:-${APP_DIR:-/app}/loggers/log_config_processed.yaml}

app:
  version: ${API_VERSION:-"0_1"}
EOL

# Process the log config template to substitute environment variables
if [ -f "${APP_DIR:-/app}/loggers/log_config.yaml" ]; then
  envsubst '${LOG_DIR} ${LOG_LEVEL}' \
    < "${APP_DIR:-/app}/loggers/log_config.yaml" \
    > "${APP_DIR:-/app}/loggers/log_config_processed.yaml"
fi

# Generate .env file for internal paths
mkdir -p "${APP_DIR:-/app}/core/settings"
cat > "${APP_DIR:-/app}/core/settings/.env" <<EOL
ENFORCER_MODEL=${APP_DIR:-/app}/core/settings/managers/policies/casbin/model.conf
ENFORCER_POLICY=${APP_DIR:-/app}/core/settings/managers/policies/casbin/policy.csv
USER_POLICIES=${APP_DIR:-/app}/data/policies
INSTANCE_CONFIGS=${APP_DIR:-/app}/data/configs
EOL

# Create empty policy file if it doesn't exist (for Casbin initialization)
mkdir -p "${APP_DIR:-/app}/core/settings/managers/policies/casbin"
touch "${APP_DIR:-/app}/core/settings/managers/policies/casbin/policy.csv"

# Ensure required environment variables are set
: "${KEYCLOAK_DOMAIN:?KEYCLOAK_DOMAIN environment variable is required}"
: "${KEYCLOAK_ADMIN_CLIENT_SECRET:?KEYCLOAK_ADMIN_CLIENT_SECRET environment variable is required}"
: "${KEYCLOAK_REDIRECT_URI:?KEYCLOAK_REDIRECT_URI environment variable is required}"

# Start the application
exec python main.py config.yaml