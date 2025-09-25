#!/bin/bash
set -e

# Defaults for logging
export LOG_DIR="${LOG_DIR:-/app/data/logs}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Fetch admin client secret from Keycloak BEFORE generating config
echo "Fetching admin client secret from Keycloak..."

# First get admin token
ADMIN_TOKEN=$(curl -s -X POST "${KEYCLOAK_DOMAIN}/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=admin-cli" \
  -d "username=${KEYCLOAK_ADMIN:-admin}" \
  -d "password=${KEYCLOAK_ADMIN_PASSWORD:-admin123}" \
  -d "grant_type=password" | \
  python3 -c "
import json, sys
try:
    token_data = json.load(sys.stdin)
    print(token_data['access_token'])
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
")

if [ -z "$ADMIN_TOKEN" ]; then
    echo "Failed to get admin token from Keycloak"
    exit 1
fi

# Get client ID
CLIENT_UUID=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients?clientId=${KEYCLOAK_ADMIN_CLIENT_ID}" | \
  python3 -c "
import json, sys
try:
    clients = json.load(sys.stdin)
    if clients and len(clients) > 0:
        print(clients[0]['id'])
    else:
        print('ERROR: Client not found', file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
")

if [ -z "$CLIENT_UUID" ]; then
    echo "Failed to get client UUID"
    exit 1
fi

# Get client secret
export KEYCLOAK_ADMIN_CLIENT_SECRET=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "${KEYCLOAK_DOMAIN}/admin/realms/${KEYCLOAK_REALM}/clients/${CLIENT_UUID}/client-secret" | \
  python3 -c "
import json, sys
try:
    secret_data = json.load(sys.stdin)
    print(secret_data['value'])
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
")

if [ -z "$KEYCLOAK_ADMIN_CLIENT_SECRET" ]; then
    echo "Failed to fetch admin client secret from Keycloak"
    exit 1
fi

echo "Admin client secret retrieved successfully: ${KEYCLOAK_ADMIN_CLIENT_SECRET:0:8}..."
echo "DEBUG: Secret length: ${#KEYCLOAK_ADMIN_CLIENT_SECRET}"
echo "DEBUG: Secret is set: $([ -n "$KEYCLOAK_ADMIN_CLIENT_SECRET" ] && echo 'YES' || echo 'NO')"

# Export the secret for the Python application
export KEYCLOAK_ADMIN_CLIENT_SECRET

echo "Admin client secret exported to environment"
echo "DEBUG: After export - Secret still set: $([ -n "$KEYCLOAK_ADMIN_CLIENT_SECRET" ] && echo 'YES' || echo 'NO')"
echo "DEBUG: Current environment KEYCLOAK_ADMIN_CLIENT_SECRET: ${KEYCLOAK_ADMIN_CLIENT_SECRET:0:8}..."

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
: "${KEYCLOAK_REDIRECT_URI:?KEYCLOAK_REDIRECT_URI environment variable is required}"

# Start the application without config file - use environment variables directly
echo "DEBUG: About to start Python with secret: ${KEYCLOAK_ADMIN_CLIENT_SECRET:0:8}..."
echo "DEBUG: Full env check before Python:"
env | grep KEYCLOAK || echo "No KEYCLOAK vars found"

# Explicitly pass the secret as an environment variable to ensure it's available
echo "DEBUG: Starting Python application..."
exec env KEYCLOAK_ADMIN_CLIENT_SECRET="$KEYCLOAK_ADMIN_CLIENT_SECRET" python main.py